"""
敏感信息脱敏工具

在消息存入记忆和日志前，自动脱敏处理以下敏感信息：
- 身份证号（18位/15位）
- 银行卡号（16-19位）
- 手机号（11位）
- 姓名（可选，在特定上下文中）
"""

import re
import logging

logger = logging.getLogger(__name__)


def mask_id_card(text: str) -> str:
    """脱敏身份证号（18位/15位）"""
    # 18位身份证
    text = re.sub(
        r'(\d{6})\d{8}(\d{3}[\dXx])',
        r'\1********\2',
        text
    )
    # 15位旧身份证
    text = re.sub(
        r'(\d{6})\d{6}(\d{3})',
        r'\1******\2',
        text
    )
    return text


def mask_bank_card(text: str) -> str:
    """脱敏银行卡号（16-19位数字）"""
    def _mask_card(match):
        card = match.group(0)
        if len(card) >= 16:
            return card[:4] + ' **** **** ' + card[-4:]
        return card
    
    text = re.sub(r'\b(\d{16,19})\b', _mask_card, text)
    return text


def mask_phone(text: str) -> str:
    """脱敏手机号（11位）"""
    text = re.sub(
        r'(\d{3})\d{4}(\d{4})',
        r'\1****\2',
        text
    )
    return text


def mask_sensitive_info(text: str) -> str:
    """
    对文本中的所有敏感信息进行脱敏处理
    
    Args:
        text: 原始文本
        
    Returns:
        脱敏后的文本
    """
    if not text or not isinstance(text, str):
        return text
    
    original = text
    text = mask_id_card(text)
    text = mask_bank_card(text)
    text = mask_phone(text)
    
    if text != original:
        logger.debug("敏感信息已脱敏处理")
    
    return text


def mask_messages(messages: list) -> list:
    """
    对消息列表中的所有消息内容进行脱敏
    
    Args:
        messages: 消息列表
        
    Returns:
        脱敏后的消息列表
    """
    masked = []
    for msg in messages:
        if hasattr(msg, 'content') and isinstance(msg.content, str):
            # 创建消息副本并脱敏
            msg_copy = msg.model_copy()
            msg_copy.content = mask_sensitive_info(msg_copy.content)
            masked.append(msg_copy)
        else:
            masked.append(msg)
    return masked
