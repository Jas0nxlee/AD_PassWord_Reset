import random
import string
import time

class VerificationService:
    def __init__(self):
        self.codes = {}
        self.code_length = 6
        self.expire_time = 300  # 验证码有效期为5分钟

    def generate_code(self, identifier):
        """为指定标识符生成验证码"""
        code = ''.join(random.choices(string.digits, k=self.code_length))
        self.codes[identifier] = {
            'code': code,
            'timestamp': time.time()
        }
        return code

    def verify_code(self, identifier, code):
        """验证指定标识符的验证码"""
        if identifier not in self.codes:
            return False
        
        stored_code_info = self.codes[identifier]
        if time.time() - stored_code_info['timestamp'] > self.expire_time:
            # 验证码已过期
            del self.codes[identifier]
            return False
        
        if stored_code_info['code'] == code:
            # 验证成功后删除验证码
            del self.codes[identifier]
            return True
        
        return False

# 实例化服务
verification_service = VerificationService()