"""Shared research taxonomy for collection, article matching and paper browsing."""
import re

TOPICS = {
    "视频生成": r"video (?:generation|diffusion|synthesis)|text.to.video|image.to.video|视频生成|生成视频|文生视频|图生视频",
    "世界模型": r"world[- ]models?|world generation|世界模型|世界生成|interactive environments?",
    "可控生成": r"controll?able (?:generation|diffusion|video|image)|controlled (?:generation|video)|camera.(?:conditioned|controlled)|motion.control|video editing|image editing|controlnet|可控生成|可控视频|相机控制|相机可控|视频编辑|图像编辑",
    "图像生成": r"image (?:generation|synthesis)|text.to.image|图像生成|文生图",
    "动态重建": r"\b4dgs\b|\b4d (?:gaussian|reconstruction)|dynamic (?:gaussian|scene reconstruction)|4d scene|动态重建|动态高斯",
    "高斯渲染": r"\b3dgs\b|gaussian splatting|splatting|radiance fields?|高斯泼溅|高斯溅射|高斯渲染|辐射场",
    "三维几何": r"multi[- ]?(?:view|camera)|camera (?:pose|models?|calibration)|\bslam\b|structure.from.motion|(?:novel[- ]view|view) synthesis|(?:3d|three.dimensional|geometric) reconstruction|depth (?:estimation|completion)|scene geometry|point clouds?|mesh(?:es)?|多视角|多视图|三维重建|深度估计|新视角合成",
    "几何基础模型": r"geometry foundation model|visual geometry foundation|\bvggt\b|\bdust3r\b|\bmast3r\b|map.?anything|depth.anything|feed[- ]?forward.{0,28}3d reconstruction|几何基础模型",
    "多模态 / 具身视觉": r"vision.language|visual.language|embodied|\bvla\b|视觉语言|具身|多模态视觉",
}

# Each family gets its own newest candidates; a high-volume field cannot crowd out the others.
ARXIV_QUERIES = {
    "视频生成": 'all:"video generation" OR all:"video diffusion" OR all:"text-to-video" OR all:"image-to-video"',
    "世界模型": 'all:"world model" OR all:"world models" OR all:"world generation"',
    "可控与图像生成": 'all:"controllable generation" OR all:"controllable video" OR all:"video editing" OR all:"image editing" OR all:"text-to-image" OR all:"camera-controlled"',
    "三维与具身视觉": 'all:"gaussian splatting" OR all:"4D reconstruction" OR all:"3D reconstruction" OR all:"geometry foundation" OR all:"VGGT" OR all:"vision-language-action"',
}

def classify(text):
    return [label for label, pattern in TOPICS.items() if re.search(pattern, text, re.I)]
