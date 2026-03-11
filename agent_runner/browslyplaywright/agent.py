from uuid import UUID
import logging
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams, SseConnectionParams
from pylibs.database_manager import get_db_manager
from db.schema import (
    Agent, AgentSkill, Skill, SkillSkill, SkillTool, Tool, 
    PythonFunction, MCPConfig, ToolType, ExecMode,
    SequentialAgentExecOrder, SequentialSkillExecOrder
)
from google.adk.models.lite_llm import LiteLlm
from google.genai import types

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

agent_id = "3fe207db-36d8-4943-aab5-37196aae5db6"


def load_python_function(session, python_function_id):
    """Load and execute Python function code from database."""
    pf = session.get(PythonFunction, python_function_id)
    if not pf:
        logger.warning(f"Python function {python_function_id} not found")
        return None
    ns = {}
    try:
        exec(pf.code, ns)
    except SyntaxError as e:
        logger.exception(f"Syntax error in tool {pf.name} at line {e.lineno}: {e.text}")
        raise
    return ns.get(pf.name)


def load_tools_for_skill(session, skill_id):
    """Load all tools (Python functions and MCP servers) for a skill."""
    tools = []
    links = session.query(SkillTool).filter(SkillTool.skill_id == skill_id).all()
    for link in links:
        tool_ob = session.get(Tool, link.tool_id)
        if not tool_ob:
            continue
        
        if tool_ob.type == ToolType.PYTHON_FUNCTION:
            try:
                fn = load_python_function(session, tool_ob.python_function_id)
                if fn:
                    tools.append(fn)
            except Exception:
                logger.exception(f"Failed loading python function tool for skill {skill_id}")
        elif tool_ob.type == ToolType.MCP_SERVER:
            try:
                cfg = session.get(MCPConfig, tool_ob.mcp_config_id)
                if not cfg:
                    continue
                c = cfg.config or {}
                transport_mode = c.get("transport_mode")
                if not transport_mode:
                    continue
                if transport_mode == "http":
                    url = cfg.url
                    tools.append(MCPToolset(connection_params=StreamableHTTPConnectionParams(url=url)))
                elif transport_mode == "sse":
                    url = cfg.url
                    tools.append(MCPToolset(connection_params=SseConnectionParams(url=url)))
                else:
                    logger.warning(f"Unknown transport mode: {transport_mode}")
                    continue
            except Exception:
                logger.exception(f"Failed loading MCP tool for skill {skill_id}")
    return tools


def _build_safety_settings(raw):
    """Convert stored JSON into google.genai.types.SafetySetting objects."""
    if not raw:
        return []
    out = []
    for item in raw:
        try:
            cat = item.get("category")
            thr = item.get("threshold")
            category_enum = (
                getattr(types.HarmCategory, cat)
                if isinstance(cat, str) and hasattr(types.HarmCategory, cat)
                else None
            )
            threshold_enum = (
                getattr(types.HarmBlockThreshold, thr)
                if isinstance(thr, str) and hasattr(types.HarmBlockThreshold, thr)
                else None
            )
            if category_enum and threshold_enum:
                out.append(
                    types.SafetySetting(category=category_enum, threshold=threshold_enum)
                )
        except Exception:
            continue
    return out


def _build_generate_content_config(obj):
    """Build GenerateContentConfig from agent/skill configuration."""
    conf_json = (
        (obj.default_model_config or {}) if hasattr(obj, "default_model_config") else {}
    )
    temp = (
        obj.temperature
        if getattr(obj, "temperature", None) is not None
        else conf_json.get("temperature", 0.2)
    )
    max_tokens = (
        obj.max_output_tokens
        if getattr(obj, "max_output_tokens", None)
        else conf_json.get("max_output_tokens", 32000)
    )
    raw_safety = (
        obj.safety_settings
        if getattr(obj, "safety_settings", None)
        else conf_json.get("safety_settings", [])
    )
    safety_objects = _build_safety_settings(raw_safety)
    return types.GenerateContentConfig(
        temperature=temp,
        max_output_tokens=max_tokens,
        safety_settings=safety_objects
    )


def build_skill_agent(session, skill, skill_cache, visiting_set):
    """
    Recursively build a skill agent based on its exec_mode.
    Returns an LlmAgent, SequentialAgent, or ParallelAgent.
    """
    if skill.id in skill_cache:
        logger.info(f"Reusing cached skill: {skill.name}")
        return skill_cache[skill.id]
    
    if skill.id in visiting_set:
        cycle_path = " -> ".join([str(sid) for sid in visiting_set]) + f" -> {skill.id}"
        error_msg = f"Cycle detected in skill hierarchy: {cycle_path}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    visiting_set.add(skill.id)
    logger.info(f"Building skill: {skill.name} (exec_mode={skill.exec_mode.value})")
    
    try:
        tools = load_tools_for_skill(session, skill.id)
        child_skills = []
        
        if skill.exec_mode == ExecMode.SEQUENTIAL:
            orders = (
                session.query(SequentialSkillExecOrder)
                .filter(SequentialSkillExecOrder.parent_skill_id == skill.id)
                .order_by(SequentialSkillExecOrder.sequence_num)
                .all()
            )
            for order in orders:
                child_skill = session.get(Skill, order.child_skill_id)
                if child_skill:
                    child_agent = build_skill_agent(session, child_skill, skill_cache, visiting_set)
                    child_skills.append(child_agent)
        
        elif skill.exec_mode == ExecMode.PARALLEL:
            skill_relations = (
                session.query(SkillSkill)
                .filter(SkillSkill.parent_skill_id == skill.id)
                .all()
            )
            for relation in skill_relations:
                child_skill = session.get(Skill, relation.child_skill_id)
                if child_skill:
                    child_agent = build_skill_agent(session, child_skill, skill_cache, visiting_set)
                    child_skills.append(child_agent)
        
        else:
            skill_relations = (
                session.query(SkillSkill)
                .filter(SkillSkill.parent_skill_id == skill.id)
                .all()
            )
            for relation in skill_relations:
                child_skill = session.get(Skill, relation.child_skill_id)
                if child_skill:
                    child_agent = build_skill_agent(session, child_skill, skill_cache, visiting_set)
                    child_skills.append(child_agent)
        
        if skill.exec_mode == ExecMode.SEQUENTIAL and child_skills:
            agent = SequentialAgent(
                name=skill.name,
                sub_agents=child_skills,
                description=skill.description or "",
            )
        elif skill.exec_mode == ExecMode.PARALLEL and child_skills:
            agent = ParallelAgent(
                name=skill.name,
                sub_agents=child_skills,
                description=skill.description or "",
            )
        else:
            llm_kwargs = {
                "name": skill.name,
                "model": LiteLlm(model=skill.default_model),
                "description": skill.description or "",
                "instruction": skill.instructions or "",
                "tools": tools,
                "generate_content_config": _build_generate_content_config(skill)
            }
            if child_skills:
                llm_kwargs["sub_agents"] = child_skills
            if skill.output_key:
                llm_kwargs["output_key"] = skill.output_key
            agent = LlmAgent(**llm_kwargs)
        
        skill_cache[skill.id] = agent
        logger.info(f"Built skill agent: {skill.name} (type={type(agent).__name__})")
        return agent
    
    finally:
        visiting_set.discard(skill.id)


def create_agent():
    """Create hierarchical agent from database with support for sequential/parallel execution."""
    session = get_db_manager().get_session()
    try:
        agent = session.get(Agent, UUID(agent_id))
        if not agent:
            raise RuntimeError(f"Agent not found: {agent_id}")
        
        logger.info(f"Creating agent: {agent.name} (exec_mode={agent.exec_mode.value})")
        
        skill_cache = {}
        visiting_set = set()
        child_agents = []
        
        if agent.exec_mode == ExecMode.SEQUENTIAL:
            orders = (
                session.query(SequentialAgentExecOrder)
                .filter(SequentialAgentExecOrder.agent_id == agent.id)
                .order_by(SequentialAgentExecOrder.sequence_num)
                .all()
            )
            for order in orders:
                skill = session.get(Skill, order.skill_id)
                if skill:
                    skill_agent = build_skill_agent(session, skill, skill_cache, visiting_set)
                    child_agents.append(skill_agent)
        
        elif agent.exec_mode == ExecMode.PARALLEL:
            links = session.query(AgentSkill).filter(AgentSkill.agent_id == agent.id).all()
            for link in links:
                skill = session.get(Skill, link.skill_id)
                if skill:
                    skill_agent = build_skill_agent(session, skill, skill_cache, visiting_set)
                    child_agents.append(skill_agent)
        
        else:
            links = session.query(AgentSkill).filter(AgentSkill.agent_id == agent.id).all()
            for link in links:
                skill = session.get(Skill, link.skill_id)
                if skill:
                    skill_agent = build_skill_agent(session, skill, skill_cache, visiting_set)
                    child_agents.append(skill_agent)
        
        if agent.exec_mode == ExecMode.SEQUENTIAL:
            root = SequentialAgent(
                name=agent.name,
                sub_agents=child_agents,
                description=agent.description or "",
            )
        elif agent.exec_mode == ExecMode.PARALLEL:
            root = ParallelAgent(
                name=agent.name,
                sub_agents=child_agents,
                description=agent.description or "",
            )
        else:
            llm_kwargs = {
                "name": agent.name,
                "model": LiteLlm(model=agent.default_model),
                "description": agent.description or "",
                "instruction": agent.instructions or "",
                "generate_content_config": _build_generate_content_config(agent)
            }
            if child_agents:
                llm_kwargs["sub_agents"] = child_agents
            if agent.output_key:
                llm_kwargs["output_key"] = agent.output_key
            root = LlmAgent(**llm_kwargs)
        
        logger.info(f"Successfully created root agent: {agent.name} (type={type(root).__name__})")
        logger.info(f"Total unique skills in hierarchy: {len(skill_cache)}")
        return root
    
    except RuntimeError as e:
        logger.error(f"Failed to create agent due to cycle: {e}")
        raise
    except Exception as e:
        logger.exception(f"Error creating agent: {e}")
        raise
    finally:
        session.close()


root_agent = create_agent()
