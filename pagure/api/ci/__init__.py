# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from pagure.config import config as pagure_config

BUILD_STATS = {
    "SUCCESS": ("Build #%s successful", pagure_config["FLAG_SUCCESS"], 100),
    "FAILURE": ("Build #%s failed", pagure_config["FLAG_FAILURE"], 0),
    "ABORTED": ("Build #%s aborted", "error", 0),
    "BUILDING": ("Build #%s in progress", pagure_config["FLAG_PENDING"], 0),
}
