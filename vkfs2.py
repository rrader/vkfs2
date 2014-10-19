import logging
import json

from vk_delegate import VKDelegate
from fuse_delegate import FuseController


if __name__ == "__main__":
    conf = json.load(open("vkfs2.conf"))
    vk = VKDelegate(conf["vk_username"], conf["vk_password"])
    # vk.wall_post()

    logging.getLogger().setLevel(logging.DEBUG)
    fuse = FuseController(conf["fuse_mountpoint"], vk)
    fuse.mount()

    # print(vk.my_audio_files())
    