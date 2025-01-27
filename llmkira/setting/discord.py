# -*- coding: utf-8 -*-
# @Time    : 2023/10/18 下午10:23
# @Author  : sudoskys
# @File    : discord.py
# @Software: PyCharm
from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseSettings, Field, validator, root_validator


class DiscordBot(BaseSettings):
    """
    代理设置
    """
    token: str = Field(None, env='DISCORD_BOT_TOKEN')
    prefix: str = Field("/", env="DISCORD_BOT_PREFIX")
    proxy_address: str = Field(None, env="DISCORD_BOT_PROXY_ADDRESS")  # "all://127.0.0.1:7890"

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'

    @validator('token')
    def proxy_address_validator(cls, v):
        if v is None:
            logger.warning(f"DiscordBot token is empty")
        return v

    @root_validator
    def bot_id_validator(cls, values):
        if values.get('token'):
            logger.success(f"DiscordBot token ready")  # {values.get('token')}")
        return values

    @property
    def available(self):
        return self.token is not None


load_dotenv()
BotSetting = DiscordBot()
