import warnings
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import requests
import torch

warnings.filterwarnings('ignore')


def get_vision_model():
    # 加载预训练的CLIP模型和处理器
    model_path = "./model/clip_model/clip-vit-base-patch32"
    model = CLIPModel.from_pretrained(model_path)
    processor = CLIPProcessor.from_pretrained(model_path)
    return (model, processor)


def get_img_process(image, processor):
    # 将图像调整为144*144大小
    image = image.resize((224, 224))
    # 使用CLIPProcessor处理每个patch
    inputs = processor(images=image, return_tensors="pt", clean_up_tokenization_spaces=False)
    return inputs


def get_img_embedding(batch_encoding, vision_model):
    embeddings = []

    def hook_fn(module, input, output):
        # 将特征添加到 embeddings 列表中
        embeddings.append(output.last_hidden_state)

    # 从 BatchEncoding 中提取图像张量
    image_tensor = batch_encoding['pixel_values']  # 假设图像张量在 'pixel_values' 键下

    # 如果图像张量的形状是5维，则无需添加额外维度
    if len(image_tensor.shape) == 4:
        image_tensor = image_tensor.unsqueeze(0)  # 添加批次维度

    # 获取批次大小
    batch_size = image_tensor.size(0)

    with torch.no_grad():
        # 注册 hook 到模型的目标层（例如 vision_model 的倒数第二层）
        layer = vision_model.vision_model.encoder
        hook = layer.register_forward_hook(hook_fn)

        for i in range(batch_size):
            # 取出当前批次中的单个图像
            single_image = image_tensor[i]  # 添加批次维度
            # 调用 get_image_features 来获取图像特征
            _ = vision_model.get_image_features(single_image)
        # 取消 hook
        hook.remove()

    # 拼接所有特征向量成为一个张量
    all_embeddings = torch.stack(embeddings, dim=0).squeeze()
    return all_embeddings