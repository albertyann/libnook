from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import requests
import uvicorn
import json

app = FastAPI(title="全文翻译API", description="基于LM Studio的多语言文本翻译服务", version="1.0.0")

class TranslationRequest(BaseModel):
    source_lang: str = "auto"  # 源语言，默认自动检测
    target_lang: str  # 目标语言，必需
    text_list: List[str]  # 要翻译的文本数组


class TranslationResponse(BaseModel):
    detected_source_lang: str
    translations: List[str]

class LMStudioTranslator:
    """LM Studio翻译器实现"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8899"):
        self.base_url = base_url
        self.model = "hy-mt1___5-1___8b@q4_k_m"
        self.chat_endpoint = f"{base_url}/v1/chat/completions"
    
    def translate(self, text: str, target_lang: str, source_lang: str = "auto") -> Dict[str, str]:
        """使用LM Studio API进行翻译"""
        
        # 如果源语言是auto，先检测语言
        # if source_lang == "auto":
        #     detected_lang = self._detect_language(text)
        # else:
        detected_lang = source_lang
        
        # 构建翻译提示词
        system_prompt = self._build_system_prompt(detected_lang, target_lang)
        user_prompt = text

        # 调用LM Studio API
        translation_result = self._call_lmstudio(system_prompt, user_prompt)
        
        return {
            "detected_source_lang": detected_lang,
            "text": translation_result
        }
    
    def _detect_language(self, text: str) -> str:
        """简单的语言检测"""
        # 使用LM Studio进行语言检测
        system_prompt = """你是一个语言检测专家。请分析用户输入的文本，判断它是什么语言。
只需返回语言代码，不要添加任何其他文本。
常见的语言代码：
- 英语: en
- 中文: zh
- 日语: ja
- 韩语: ko
- 法语: fr
- 德语: de
- 西班牙语: es
- 俄语: ru
- 意大利语: it
- 葡萄牙语: pt"""
        
        user_prompt = f"请检测以下文本的语言，只返回语言代码：\n\n{text}"
        
        try:
            response = requests.post(
                self.chat_endpoint,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 10
                },
                timeout=10
            )
            print(response)
            if response.status_code == 200:
                result = response.json()
                detected_lang = result.get("choices", [{}])[0].get("message", {}).get("content", "en").strip()
                return detected_lang if detected_lang in ["en", "zh", "ja", "ko", "fr", "de", "es", "ru", "it", "pt"] else "en"
        except:
            pass
        
        # 如果检测失败，使用简单的启发式方法
        return self._simple_language_detection(text)
    
    def _simple_language_detection(self, text: str) -> str:
        """简单的启发式语言检测"""
        if any('\u4e00' <= c <= '\u9fff' for c in text):  # 中文字符
            return "zh"
        elif any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' for c in text):  # 日文字符
            return "ja"
        elif any('\uac00' <= c <= '\ud7af' for c in text):  # 韩文字符
            return "ko"
        elif any(c.isalpha() and ord(c) > 127 for c in text):  # 其他非英语拉丁字母
            # 简单的欧洲语言检测
            text_lower = text.lower()
            if ' de ' in text_lower or ' und ' in text_lower:
                return "de"
            elif ' le ' in text_lower or ' la ' in text_lower or ' et ' in text_lower:
                return "fr"
            elif ' el ' in text_lower or ' y ' in text_lower:
                return "es"
            else:
                return "en"
        else:
            return "en"
    
    def _build_system_prompt(self, source_lang: str, target_lang: str) -> str:
        """构建翻译系统提示词"""

        return f"""你是一个专业的翻译助手。请将用户输入的英语文本翻译成中文。

翻译要求：
1. 保持原文的意思和语气不变
2. 使用自然流畅的中文表达
3. 保留专业术语和专有名词
4. 如果是口语化表达，请用自然的口语翻译
5. 只返回翻译后的文本，不要添加任何解释或说明

现在，请翻译用户输入的文本。"""
    
    def _call_lmstudio(self, system_prompt: str, user_prompt: str) -> str:
        """调用LM Studio API"""
        try:
            response = requests.post(
                self.chat_endpoint,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1000,
                    "stream": False
                },
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                translation = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                return translation
            else:
                print(f"LM Studio API错误: {response.status_code} - {response.text}")
                return f"[翻译失败] {user_prompt}"
                
        except requests.exceptions.ConnectionError:
            print("LM studio:", self.chat_endpoint)
            print("无法连接到LM Studio，请确保LM Studio正在运行")
            return f"[连接失败] {user_prompt}"
        except requests.exceptions.Timeout:
            print("LM studio:", self.chat_endpoint)
            print("LM Studio响应超时")
            return f"[超时] {user_prompt}"
        except Exception as e:
            print(f"调用LM Studio时发生错误: {e}")
            return f"[错误] {user_prompt}"
    
    def batch_translate(self, texts: List[str], target_lang: str, source_lang: str = "auto") -> List[Dict[str, str]]:
        """批量翻译文本"""
        results = []
        
        for i, text in enumerate(texts):
            if not text or not text.strip():
                results.append({
                    "detected_source_lang": source_lang if source_lang != "auto" else "unknown",
                    "text": ""
                })
                continue

            result = self.translate(text, target_lang, source_lang)
            results.append(result)

        return results


# 初始化翻译器
translator = LMStudioTranslator(base_url="http://127.0.0.1:8899")

@app.post("/v1/imme", summary="批量文本翻译")
async def translate_text(request: TranslationRequest):
    """
    批量翻译文本接口
    
    - **source_lang**: 源语言代码（如 en, zh, ja），默认为 "auto" 自动检测
    - **target_lang**: 目标语言代码（必需）
    - **text_list**: 要翻译的文本数组
    
    返回包含翻译结果和检测到的源语言的响应
    """
    if not request.text_list:
        raise HTTPException(status_code=400, detail="text_list不能为空")
    
    if not request.target_lang:
        raise HTTPException(status_code=400, detail="target_lang是必需参数")
    
    # 批量翻译
    translation_results = translator.batch_translate(
        texts       = request.text_list,
        target_lang = request.target_lang,
        source_lang = request.source_lang
    )
    
    # 提取结果
    translations = [{
        'detected_source_lang': result["detected_source_lang"],
        'translations': result['text']
    } for result in translation_results]

    return translations


@app.post("/v1/translate/single", summary="单条文本翻译")
async def translate_single_text(request: TranslationRequest):
    """
    单条文本翻译接口（方便测试）
    """
    if not request.text_list:
        raise HTTPException(status_code=400, detail="text_list不能为空")
    
    if not request.target_lang:
        raise HTTPException(status_code=400, detail="target_lang是必需参数")
    
    # 只处理第一条文本
    text = request.text_list[0]
    result = translator.translate(text, request.target_lang, request.source_lang)
    
    return {
        "detected_source_lang": result["detected_source_lang"],
        "translation": result["text"],
        "original": text,
        "source_lang": request.source_lang,
        "target_lang": request.target_lang
    }


@app.get("/")
async def root():
    """根路径，返回API信息"""
    return {
        "name": "基于LM Studio的全文翻译API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "批量翻译": "POST /v1/imme",
            "单条翻译": "POST /v1/translate/single",
            "健康检查": "GET /health"
        },
        "lm_studio_url": translator.base_url
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        # 测试LM Studio连接
        response = requests.get(f"{translator.base_url}/v1/models", timeout=5)
        lm_status = "connected" if response.status_code == 200 else "disconnected"
    except:
        lm_status = "disconnected"
    
    return {
        "status": "healthy",
        "service": "lm-studio-translation-api",
        "lm_studio": lm_status,
        "endpoints": {
            "translation": "/v1/imme",
            "single_translation": "/v1/translate/single"
        }
    }


@app.get("/languages")
async def get_supported_languages():
    """获取支持的语言列表"""
    return {
        "supported_languages": {
            "en": "English",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "fr": "French",
            "de": "German",
            "es": "Spanish",
            "ru": "Russian",
            "it": "Italian",
            "pt": "Portuguese"
        },
        "auto_detection": True
    }

if __name__ == "__main__":
    print("=" * 60)
    print("基于LM Studio的翻译API")
    print(f"服务地址: http://127.0.0.1:8090")
    print(f"LM Studio地址: {translator.base_url}")
    print("=" * 60)
    print("\n请确保LM Studio正在运行，并加载了合适的模型。")
    print("访问 http://127.0.0.1:8090/docs 查看API文档")
    
    uvicorn.run(
        app,
        host = "127.0.0.1",
        port = 8090,
        log_level = "info"
    )