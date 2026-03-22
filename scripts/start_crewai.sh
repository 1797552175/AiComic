#!/bin/bash
# CrewAI 运行时容器启动脚本
# 用途：启动 crewai-runtime 容器并挂载 /opt/AiComic

set -e

CONTAINER_NAME="crewai-runtime"
IMAGE="python:3.11-slim"
VOLUME_SRC="/opt/AiComic"
VOLUME_DST="/opt/AiComic"

# 如果容器已存在，先停止并删除
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "容器已存在，重新创建..."
    docker stop ${CONTAINER_NAME} 2>/dev/null || true
    docker rm ${CONTAINER_NAME} 2>/dev/null || true
fi

# 启动容器（带 volume 挂载）
docker run -d \
  --name ${CONTAINER_NAME} \
  -v ${VOLUME_SRC}:${VOLUME_DST} \
  -w ${VOLUME_DST} \
  ${IMAGE} \
  sleep infinity

echo "容器 ${CONTAINER_NAME} 已启动"

# 安装 crewai（如需要）
docker exec ${CONTAINER_NAME} pip install crewai crewai-tools -q 2>/dev/null || true

echo "安装 crewai 完成"

# 创建输出目录
docker exec ${CONTAINER_NAME} mkdir -p ${VOLUME_DST}/scripts/output

echo "===== CrewAI 运行时就绪 ====="
echo "容器: ${CONTAINER_NAME}"
echo "挂载: ${VOLUME_SRC} -> ${VOLUME_DST}"
echo "执行命令: docker exec ${CONTAINER_NAME} python /opt/AiComic/scripts/generated/<脚本>.py"
