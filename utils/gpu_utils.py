"""GPU工具模块 - 检测和管理GPU资源"""
import torch


def check_cuda_available():
    """检测CUDA是否可用"""
    return torch.cuda.is_available()


def get_gpu_info():
    """获取GPU信息"""
    if not check_cuda_available():
        return None
    
    gpu_info = {
        'name': torch.cuda.get_device_name(0),
        'count': torch.cuda.device_count(),
        'current_device': torch.cuda.current_device()
    }
    return gpu_info


def get_gpu_memory_info():
    """获取显存使用情况（MB）"""
    if not check_cuda_available():
        return None
    
    allocated = torch.cuda.memory_allocated(0) / 1024 / 1024
    reserved = torch.cuda.memory_reserved(0) / 1024 / 1024
    total = torch.cuda.get_device_properties(0).total_memory / 1024 / 1024
    
    return {
        'allocated': allocated,
        'reserved': reserved,
        'total': total,
        'free': total - allocated
    }


def estimate_batch_size(available_memory_mb=None):
    """根据可用显存估算合适的batch_size"""
    if not check_cuda_available():
        return 16  # CPU模式使用较小的batch
    
    if available_memory_mb is None:
        mem_info = get_gpu_memory_info()
        available_memory_mb = mem_info['free']
    
    # CLIP ViT-B/32每个batch大约需要15MB显存
    # 保守估计，留出缓冲空间
    estimated_batch = int(available_memory_mb / 20)
    
    # 限制在合理范围内
    return max(8, min(estimated_batch, 64))


def clear_gpu_cache():
    """清理GPU缓存"""
    if check_cuda_available():
        torch.cuda.empty_cache()
