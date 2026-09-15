"""BluEcho: offline sonar inference and physics-aware inspection."""
__version__ = '0.5.1'
__all__ = ['Engine', 'InputError', 'ModelError', 'RecordingEngine', 'InspectionSupervisor']

def __getattr__(name):
    if name in ('Engine','InputError','ModelError'):
        from . import engine
        return getattr(engine,name)
    if name=='RecordingEngine':
        from .phase1.engine import RecordingEngine
        return RecordingEngine
    if name=='InspectionSupervisor':
        from .inspection.supervisor import InspectionSupervisor
        return InspectionSupervisor
    raise AttributeError(name)
