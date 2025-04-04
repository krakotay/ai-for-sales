from sql_agents import orchestrator_agent, synthesizer_agent
from agents.extensions.visualization import draw_graph





draw_graph(orchestrator_agent).view()
draw_graph(synthesizer_agent).view()
