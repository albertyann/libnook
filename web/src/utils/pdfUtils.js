import * as pdfjsLib from 'pdfjs-dist';

// 配置PDF.js使用worker，直接使用CDN URL
pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://unpkg.com/pdfjs-dist@3.10.111/build/pdf.worker.js';

/**
 * 解析PDF文件，返回各页面信息
 * @param {File} pdfFile - PDF文件对象
 * @returns {Promise<Array>} - 包含各页面信息的数组
 */
export async function parsePdf(pdfFile) {
  try {
    // 将File对象转换为ArrayBuffer
    const arrayBuffer = await readFileAsArrayBuffer(pdfFile);
    
    // 加载PDF文档
    const pdfDoc = await pdfjsLib.getDocument({
      data: arrayBuffer,
      cMapUrl: 'https://unpkg.com/pdfjs-dist@3.10.111/cmaps/',
      cMapPacked: true
    }).promise;
    
    const totalPages = pdfDoc.numPages;
    const pages = [];
    
    // 逐页处理
    for (let pageNum = 1; pageNum <= totalPages; pageNum++) {
      const page = await pdfDoc.getPage(pageNum);
      
      // 获取页面文本内容
      const content = await page.getTextContent();
      const text = content.items.map(item => item.str).join('');
      
      // 获取页面信息
      const viewport = page.getViewport({ scale: 1.0 });
      
      pages.push({
        pageNum,
        text,
        width: viewport.width,
        height: viewport.height,
        pdfFileId: pdfFile.name + pdfFile.lastModified
      });
    }
    
    return {
      fileName: pdfFile.name,
      fileSize: pdfFile.size,
      lastModified: pdfFile.lastModified,
      totalPages,
      pages
    };
  } catch (error) {
    console.error('解析PDF文件失败:', error);
    throw new Error('PDF解析失败: ' + error.message);
  }
}

/**
 * 生成PDF页面的缩略图
 * @param {File} pdfFile - PDF文件对象
 * @param {number} pageNum - 页码（从1开始）
 * @param {Object} options - 选项
 * @param {number} options.width - 缩略图宽度
 * @param {number} options.height - 缩略图高度
 * @returns {Promise<string>} - 缩略图的DataURL
 */
export async function generatePdfThumbnail(pdfFile, pageNum, options = {}) {
  try {
    const { width = 200, height } = options;
    
    // 将File对象转换为ArrayBuffer
    const arrayBuffer = await readFileAsArrayBuffer(pdfFile);
    
    // 加载PDF文档
    const pdfDoc = await pdfjsLib.getDocument({
      data: arrayBuffer,
      cMapUrl: 'https://unpkg.com/pdfjs-dist@3.10.111/cmaps/',
      cMapPacked: true
    }).promise;
    
    // 获取指定页面
    const page = await pdfDoc.getPage(pageNum);
    
    // 计算缩放比例
    const viewport = page.getViewport({ scale: 1.0 });
    const scale = width / viewport.width;
    const scaledViewport = page.getViewport({ scale });
    
    // 创建canvas元素
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.width = scaledViewport.width;
    canvas.height = scaledViewport.height;
    
    // 渲染页面到canvas
    const renderContext = {
      canvasContext: context,
      viewport: scaledViewport
    };
    
    await page.render(renderContext).promise;
    
    // 转换为DataURL
    return canvas.toDataURL('image/png');
  } catch (error) {
    console.error('生成PDF缩略图失败:', error);
    throw new Error('缩略图生成失败: ' + error.message);
  }
}

/**
 * 为PDF文件的所有页面生成缩略图
 * @param {File} pdfFile - PDF文件对象
 * @param {Object} options - 缩略图选项
 * @returns {Promise<Array>} - 包含各页面缩略图的数组
 */
export async function generateAllThumbnails(pdfFile, options = {}) {
  try {
    const arrayBuffer = await readFileAsArrayBuffer(pdfFile);
    const pdfDoc = await pdfjsLib.getDocument({
      data: arrayBuffer,
      cMapUrl: 'https://unpkg.com/pdfjs-dist@3.10.111/cmaps/',
      cMapPacked: true
    }).promise;
    
    const totalPages = pdfDoc.numPages;
    const thumbnails = [];
    
    for (let pageNum = 1; pageNum <= totalPages; pageNum++) {
      const thumbnail = await generatePdfThumbnail(pdfFile, pageNum, options);
      thumbnails.push({
        pageNum,
        thumbnailUrl: thumbnail
      });
    }
    
    return thumbnails;
  } catch (error) {
    console.error('生成所有缩略图失败:', error);
    throw new Error('批量生成缩略图失败: ' + error.message);
  }
}

/**
 * 将File对象转换为ArrayBuffer
 * @param {File} file - 文件对象
 * @returns {Promise<ArrayBuffer>} - ArrayBuffer数据
 */
function readFileAsArrayBuffer(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error('文件读取失败'));
    reader.readAsArrayBuffer(file);
  });
}

/**
 * 合并PDF解析和缩略图生成的功能
 * @param {File} pdfFile - PDF文件对象
 * @param {Object} thumbnailOptions - 缩略图选项
 * @returns {Promise<Object>} - 包含PDF信息和缩略图的完整数据
 */
export async function processPdfFile(pdfFile, thumbnailOptions = {}) {
  try {
    // 解析PDF获取页面信息
    const pdfInfo = await parsePdf(pdfFile);
    
    // 生成所有页面的缩略图
    const thumbnails = await generateAllThumbnails(pdfFile, thumbnailOptions);
    
    // 合并页面信息和缩略图
    const pagesWithThumbnails = pdfInfo.pages.map(page => ({
      ...page,
      thumbnailUrl: thumbnails.find(t => t.pageNum === page.pageNum)?.thumbnailUrl
    }));
    
    return {
      ...pdfInfo,
      pages: pagesWithThumbnails,
      processedAt: new Date().toISOString()
    };
  } catch (error) {
    console.error('处理PDF文件失败:', error);
    throw error;
  }
}