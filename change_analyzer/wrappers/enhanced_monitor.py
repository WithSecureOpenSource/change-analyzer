import gym as gym
from gym.wrappers import Monitor

from change_analyzer.wrappers.transparent_wrapper_mixin import TransparentWrapperMixin


class EnhancedMonitor(Monitor, TransparentWrapperMixin):
    def __init__(
        self,
        env: gym.Env,
        directory: str,
        video_callable=None,
        force=False,
        resume=False,
        write_upon_reset=False,
        uid=None,
        mode=None,
    ) -> None:
        super(EnhancedMonitor, self).__init__(
            env, directory, video_callable, force, resume, write_upon_reset, uid, mode
        )
