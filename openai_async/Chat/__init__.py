# -*- coding: utf-8 -*-
# @Time    : 12/6/22 12:02 PM
# @FileName: chat.py
# @Software: PyCharm
# @Github    ：sudoskys
import json
import os

import jiagu
import nltk

nltk.download('punkt')
nltk.download('stopwords')

# 基于 Completion 上层
from openai_async import Completion
from ..utils.data import MsgFlow


class Chatbot(object):
    def __init__(self, api_key, conversation_id, call_func=None):
        """
        chatGPT 的实现由上下文实现，所以我会做一个存储器来获得上下文
        :param api_key:
        :param conversation_id: 独立ID,每个场景需要独一个
        :param call_func: 回调
        """
        self._api_key = api_key
        self.conversation_id = conversation_id
        self._MsgFlow = MsgFlow(uid=self.conversation_id)
        self._start_sequence = "\nAI:"
        self._restart_sequence = "\nHuman: "
        self.__call_func = call_func
        self.__token_limit = 2568

    def reset_chat(self):
        # Forgets conversation
        return self._MsgFlow.forget()

    @staticmethod
    def tokenizer(s: str) -> float:
        """
        谨慎的计算器，会预留 5 token
        :param s:
        :return:
        """
        # 统计中文字符数量
        num_chinese = len([c for c in s if ord(c) > 127])
        # 统计非中文字符数量
        num_non_chinese = len([c for c in s if ord(c) <= 127])
        return int(num_chinese * 2 + num_non_chinese * 0.25) + 5

    def record_ai(self, prompt, response):
        REPLY = []
        Choice = response.get("choices")
        if Choice:
            for item in Choice:
                _text = item.get("text")
                REPLY.append(_text)
        if not REPLY:
            REPLY = ["(Ai Say Nothing)"]
        self._MsgFlow.save(prompt=prompt, role=self._restart_sequence)
        self._MsgFlow.save(prompt=REPLY[0], role=self._start_sequence)
        return REPLY

    @staticmethod
    def random_string(length):
        import string  # 导入string模块
        import random  # 导入random模块

        all_chars = string.ascii_letters + string.digits  # 获取所有字符，包括大小写字母和数字

        result = ''  # 创建一个空字符串用于保存生成的随机字符

        for i in range(length):
            result += random.choice(all_chars)  # 随机选取一个字符，并添加到result中

        return result  # 返回生成的随机字符

    # _prompt = random_string(3700)

    def get_hash(self):
        import hashlib
        my_string = str(self.conversation_id)
        # 使用 hashlib 模块中的 sha256 算法创建一个散列对象
        hash_object = hashlib.sha256(my_string.encode())
        return hash_object.hexdigest()

    @staticmethod
    def zip_str(_item):
        # 读取字典
        path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), ".", "vocab.json")
        )
        with open(path, encoding="utf8") as f:
            target = json.loads(f.read())
        # 遍历字典键值对
        for key, value in target.items():
            # 使用 str.replace() 方法替换字符串中的键
            _item = _item.replace(key, value)
        return _item

    @staticmethod
    def summary(sentence, n):
        """
        :param sentence: 字符串
        :param n: 几句话
        :return: 总结
        """
        # 差缺中文系统
        _chinese = False
        # 统计中文字符数量
        if len([c for c in sentence if ord(c) > 127]) / len(sentence) > 0.5:
            _chinese = True
        if _chinese:
            try:
                _sum = jiagu.summarize(sentence, round(n / 10))
            except Exception as e:
                _sum = [sentence]
            content = ",".join(_sum)  # 摘要
        else:
            tokens = nltk.word_tokenize(sentence)
            # 分句
            sentences = nltk.sent_tokenize(sentence)
            # 计算词频
            frequencies = nltk.FreqDist(tokens)
            # 计算每个句子的得分
            scores = {}
            for sentence_ in sentences:
                score = 0
                for word in nltk.word_tokenize(sentence_):
                    if word in frequencies:
                        score += frequencies[word]
                scores[sentence_] = score
            # 按照得分顺序排序句子
            sorted_sentences = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            # 返回前 num_sentences 个句子
            return_num = round(n / 2)
            if len(sorted_sentences) < return_num:
                return_num = len(sorted_sentences)
            _list = [sentence_[0] for sentence_ in sorted_sentences[:return_num]]
            content = ",".join(_list)
        if len(content.strip(" ")) == 0:
            content = sentence
        return content

    def cutter(self, chat_list: list, extra_token: int = 0) -> list:
        """
        负责提炼截断对话
        :param extra_token: 换行符号预期会占用的位置
        :param chat_list: 对话字符串列表
        :return: 新的列表
        """
        if len(chat_list) < 5:
            return chat_list
        # 真正开始
        _new_list = []
        _limit = self.__token_limit - extra_token
        # 预设转移
        _new_list.append(chat_list.pop(0))
        # 保留比
        _real = _limit * 0.75
        # 保留段数据的初步语义处理和计算切片位置
        real_length = 0
        cutoff_index = -1
        _real_list = []
        for i in reversed(range(len(chat_list))):
            content = chat_list[i]
            # 压缩数据
            _corn = content.split(":", 1)
            if len(_corn) > 1:
                _head = _corn[0]
                if _corn[1].isspace() or len(_corn[1]) == 0:
                    continue
                _talk = self.zip_str(_corn[1])
                content = f"{_head}: {_talk}"
            else:
                content = self.zip_str(_corn[0])
            _real_list.append(content)
            string_length = self.tokenizer(content)
            real_length += string_length
            if real_length > _real:
                cutoff_index = i
                break
        # 抛弃段能简化则简化
        after = _limit - real_length
        after_length = 0
        _after_list = []
        _nlp = chat_list[:cutoff_index]
        for i in reversed(range(len(_nlp))):
            content = _nlp[i]
            # 压缩数据
            _item = self.tokenizer(content)
            if _item > 7:
                _corn = content.split(":", 1)
                if len(_corn) > 1:
                    _head = _corn[0]
                    if _corn[1].isspace() or len(_corn[1]) == 0:
                        continue
                    _talk = self.summary(_corn[1], round(_item / 7))
                    content = f"{_head}: {_talk}"
                else:
                    content = self.summary(_corn[0], round(_item / 7))
                _fate = self.tokenizer(content)
                after_length = after_length + _fate
                _after_list.append(content)
                if after_length > after:
                    break
        _new_list.extend(reversed(_after_list))
        _new_list.extend(reversed(_real_list))
        return _new_list

    async def get_chat_response(self, prompt: str, max_tokens: int = 150, model: str = "text-davinci-003",
                                character: list = None, head: str = None) -> dict:
        """
        异步的，得到对话上下文
        :param head: 预设技巧
        :param max_tokens: 限制返回字符数量
        :param model: 模型选择
        :param prompt: 提示词
        :param character: 性格提示词，列表字符串
        :return:
        """
        # 预设
        if head is None:
            head = f"\nHuman: 你好，让我们开始愉快的谈话！\nAI: 我是 Ai assistant 请问?"
        if character is None:
            character = ["helpful", "creative", "clever", "friendly", "lovely", "talkative"]
        _character = ",".join(character)
        # 初始化
        _role = f"The following is a conversation with Ai assistant. The assistant is {_character}."
        _old = self._MsgFlow.read()
        # 构造内容
        _head = [f"{_role}\n{head}\n"]
        _old_list = [f"{x['role']} {x['prompt']}" for x in _old]
        _now = [f"{self._restart_sequence}{prompt}."]
        # 拼接
        _prompt_table = _head + _old_list + _now
        # 截断器
        _prompt_apple = self.cutter(_prompt_table,
                                    extra_token=int(len(_prompt_table) + self.tokenizer(self._start_sequence))
                                    )
        _header = _prompt_apple.pop(0)
        _prompt = '\n'.join(_prompt_apple) + f"\n{self._start_sequence}"  # 这里的上面要额外 （条目数量） 计算代币 /n 占一个空格
        # 重切割代币
        _mk = self.__token_limit - self.tokenizer(_header)  # 余量？

        if _mk < 0:
            _mk = 0
        while self.tokenizer(_prompt) > _mk:
            _prompt = _prompt[1:]
        if _mk > 0:
            _prompt = _header + _prompt
        response = await Completion(api_key=self._api_key, call_func=self.__call_func).create(
            model=model,
            prompt=_prompt,
            temperature=0.9,
            max_tokens=max_tokens,
            top_p=1,
            n=1,
            frequency_penalty=0,
            presence_penalty=0.5,
            user=str(self.get_hash()),
            stop=["Human:", "AI:"],
        )
        self.record_ai(prompt=prompt, response=response)
        return response
