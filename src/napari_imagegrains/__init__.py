
try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"

from .imgr_proc_widget import ImageGrainProcWidget
from .imgr_stats_widget import ImageGrainStatsWidget
from .imgr_demodata_widget import ImageGrainDemoWidget

__all__ = (
    "ImageGrainProcWidget",
    "ImageGrainStatsWidget",
    "ImageGrainDemoWidget",
)
