#!/bin/bash

# 工友权益明白人 - 快速部署脚本

echo "=========================================="
echo "  工友权益明白人 - 部署工具"
echo "=========================================="
echo ""

# 检查是否安装了vercel CLI
if ! command -v vercel &> /dev/null; then
    echo "❌ 未检测到Vercel CLI"
    echo ""
    echo "请先安装Vercel CLI："
    echo "  npm install -g vercel"
    echo ""
    echo "或者使用其他方式部署："
    echo "  1. 访问 https://vercel.com"
    echo "  2. 点击「New Project」"
    echo "  3. 选择「Upload」"
    echo "  4. 拖拽 frontend/index.html 文件"
    echo "  5. 点击「Deploy」"
    exit 1
fi

echo "✅ 检测到Vercel CLI"
echo ""

# 检查frontend目录
if [ ! -f "frontend/index.html" ]; then
    echo "❌ 未找到 frontend/index.html"
    echo "请在项目根目录运行此脚本"
    exit 1
fi

echo " 找到 frontend/index.html"
echo ""

# 创建临时部署目录
TEMP_DIR=$(mktemp -d)
echo " 创建临时目录：$TEMP_DIR"

# 复制文件
cp frontend/index.html "$TEMP_DIR/"
echo "✅ 复制文件到临时目录"

# 进入临时目录
cd "$TEMP_DIR"

echo ""
echo "🚀 开始部署到Vercel..."
echo ""

# 部署
vercel --yes

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo ""
echo "📝 下一步："
echo "  1. 在扣子平台获取WebSDK token"
echo "  2. 更新 index.html 中的 token"
echo "  3. 重新部署"
echo ""
echo "🔗 访问链接已在上方显示"
echo ""

# 清理临时目录
cd /workspace/projects
rm -rf "$TEMP_DIR"
echo "✅ 清理临时目录"
