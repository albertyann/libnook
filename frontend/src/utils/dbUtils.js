/**
 * 浏览器本地数据库操作工具类
 * 使用IndexedDB存储PDF解析数据和缩略图
 */

// 数据库名称和版本
const DB_NAME = 'OCR_PDF_DB';
const DB_VERSION = 1;

// 存储对象名称
const STORES = {
  PDF_FILES: 'pdf_files',
  PDF_PAGES: 'pdf_pages',
  THUMBNAILS: 'thumbnails'
};

/**
 * 打开数据库连接
 * @returns {Promise<IDBDatabase>} - 数据库连接对象
 */
export async function openDatabase() {
  return new Promise((resolve, reject) => {
    if (!('indexedDB' in window)) {
      reject(new Error('您的浏览器不支持IndexedDB'));
      return;
    }

    const request = window.indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = (event) => {
      reject(new Error('数据库打开失败: ' + event.target.error));
    };

    request.onsuccess = (event) => {
      resolve(event.target.result);
    };

    // 数据库版本升级或首次创建时执行
    request.onupgradeneeded = (event) => {
      const db = event.target.result;

      // 创建PDF文件信息存储
      if (!db.objectStoreNames.contains(STORES.PDF_FILES)) {
        const pdfFilesStore = db.createObjectStore(STORES.PDF_FILES, { keyPath: 'fileId' });
        pdfFilesStore.createIndex('fileName', 'fileName', { unique: false });
        pdfFilesStore.createIndex('processedAt', 'processedAt', { unique: false });
      }

      // 创建PDF页面信息存储
      if (!db.objectStoreNames.contains(STORES.PDF_PAGES)) {
        const pdfPagesStore = db.createObjectStore(STORES.PDF_PAGES, { keyPath: 'pageId' });
        pdfPagesStore.createIndex('pdfFileId', 'pdfFileId', { unique: false });
        pdfPagesStore.createIndex('pageNum', 'pageNum', { unique: false });
        pdfPagesStore.createIndex('pdfFileId_pageNum', ['pdfFileId', 'pageNum'], { unique: true });
      }

      // 创建缩略图存储
      if (!db.objectStoreNames.contains(STORES.THUMBNAILS)) {
        const thumbnailsStore = db.createObjectStore(STORES.THUMBNAILS, { keyPath: 'thumbnailId' });
        thumbnailsStore.createIndex('pdfFileId', 'pdfFileId', { unique: false });
        thumbnailsStore.createIndex('pageNum', 'pageNum', { unique: false });
      }
    };
  });
}

/**
 * 执行数据库事务
 * @param {string} storeName - 存储对象名称
 * @param {string} mode - 事务模式 ('readonly' 或 'readwrite')
 * @param {Function} callback - 事务回调函数
 * @returns {Promise<any>} - 事务结果
 */
async function transaction(storeName, mode, callback) {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(storeName, mode);
    const store = transaction.objectStore(storeName);

    transaction.onerror = (event) => {
      reject(new Error('事务执行失败: ' + event.target.error));
    };

    transaction.oncomplete = () => {
      db.close();
    };

    try {
      const result = callback(store);
      if (result instanceof IDBRequest) {
        result.onsuccess = () => resolve(result.result);
        result.onerror = () => reject(new Error('请求执行失败: ' + result.error));
      } else {
        resolve(result);
      }
    } catch (error) {
      reject(error);
    }
  });
}

/**
 * 保存PDF文件信息
 * @param {Object} pdfInfo - PDF文件信息
 * @returns {Promise<string>} - 保存的文件ID
 */
export async function savePdfFile(pdfInfo) {
  const fileId = pdfInfo.fileName + pdfInfo.lastModified;
  const pdfFileData = {
    fileId,
    fileName: pdfInfo.fileName,
    fileSize: pdfInfo.fileSize,
    lastModified: pdfInfo.lastModified,
    totalPages: pdfInfo.totalPages,
    processedAt: pdfInfo.processedAt || new Date().toISOString()
  };

  await transaction(STORES.PDF_FILES, 'readwrite', (store) => {
    return store.put(pdfFileData);
  });

  return fileId;
}

/**
 * 保存PDF页面信息
 * @param {string} pdfFileId - PDF文件ID
 * @param {Array} pages - 页面信息数组
 * @returns {Promise<void>}
 */
export async function savePdfPages(pdfFileId, pages) {
  // 先删除该文件的所有旧页面数据
  await deletePdfPages(pdfFileId);

  // 批量保存新页面数据
  const pagePromises = pages.map(async (page) => {
    const pageId = `${pdfFileId}_page_${page.pageNum}`;
    const pageData = {
      pageId,
      pdfFileId,
      pageNum: page.pageNum,
      text: page.text,
      width: page.width,
      height: page.height
    };

    await transaction(STORES.PDF_PAGES, 'readwrite', (store) => {
      return store.add(pageData);
    });

    // 同时保存缩略图
    if (page.thumbnailUrl) {
      await saveThumbnail(pdfFileId, page.pageNum, page.thumbnailUrl);
    }
  });

  await Promise.all(pagePromises);
}

/**
 * 保存缩略图
 * @param {string} pdfFileId - PDF文件ID
 * @param {number} pageNum - 页码
 * @param {string} thumbnailUrl - 缩略图DataURL
 * @returns {Promise<void>}
 */
export async function saveThumbnail(pdfFileId, pageNum, thumbnailUrl) {
  const thumbnailId = `${pdfFileId}_thumbnail_${pageNum}`;
  const thumbnailData = {
    thumbnailId,
    pdfFileId,
    pageNum,
    thumbnailUrl,
    createdAt: new Date().toISOString()
  };

  await transaction(STORES.THUMBNAILS, 'readwrite', (store) => {
    return store.put(thumbnailData);
  });
}

/**
 * 获取所有PDF文件列表
 * @returns {Promise<Array>} - PDF文件列表
 */
export async function getAllPdfFiles() {
  return transaction(STORES.PDF_FILES, 'readonly', (store) => {
    return store.getAll();
  });
}

/**
 * 根据文件ID获取PDF文件信息
 * @param {string} fileId - 文件ID
 * @returns {Promise<Object|null>} - PDF文件信息
 */
export async function getPdfFile(fileId) {
  return transaction(STORES.PDF_FILES, 'readonly', (store) => {
    return store.get(fileId);
  });
}

/**
 * 获取指定PDF文件的所有页面
 * @param {string} pdfFileId - PDF文件ID
 * @returns {Promise<Array>} - 页面列表
 */
export async function getPdfPages(pdfFileId) {
  return transaction(STORES.PDF_PAGES, 'readonly', (store) => {
    const index = store.index('pdfFileId');
    return index.getAll(pdfFileId);
  });
}

/**
 * 获取指定页面的缩略图
 * @param {string} pdfFileId - PDF文件ID
 * @param {number} pageNum - 页码
 * @returns {Promise<string|null>} - 缩略图URL
 */
export async function getThumbnail(pdfFileId, pageNum) {
  try {
    const thumbnailId = `${pdfFileId}_thumbnail_${pageNum}`;
    const thumbnail = await transaction(STORES.THUMBNAILS, 'readonly', (store) => {
      return store.get(thumbnailId);
    });
    return thumbnail ? thumbnail.thumbnailUrl : null;
  } catch (error) {
    console.error('获取缩略图失败:', error);
    return null;
  }
}

/**
 * 删除PDF文件及其相关数据
 * @param {string} fileId - 文件ID
 * @returns {Promise<void>}
 */
export async function deletePdfFile(fileId) {
  // 删除文件信息
  await transaction(STORES.PDF_FILES, 'readwrite', (store) => {
    return store.delete(fileId);
  });

  // 删除相关页面
  await deletePdfPages(fileId);

  // 删除相关缩略图
  await deleteThumbnails(fileId);
}

/**
 * 删除指定PDF文件的所有页面
 * @param {string} pdfFileId - PDF文件ID
 * @returns {Promise<void>}
 */
async function deletePdfPages(pdfFileId) {
  const pages = await getPdfPages(pdfFileId);
  const deletePromises = pages.map(page => 
    transaction(STORES.PDF_PAGES, 'readwrite', (store) => {
      return store.delete(page.pageId);
    })
  );
  await Promise.all(deletePromises);
}

/**
 * 删除指定PDF文件的所有缩略图
 * @param {string} pdfFileId - PDF文件ID
 * @returns {Promise<void>}
 */
async function deleteThumbnails(pdfFileId) {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(STORES.THUMBNAILS, 'readwrite');
    const store = transaction.objectStore(STORES.THUMBNAILS);
    const index = store.index('pdfFileId');
    const request = index.openCursor(pdfFileId);

    request.onsuccess = (event) => {
      const cursor = event.target.result;
      if (cursor) {
        cursor.delete();
        cursor.continue();
      }
    };

    transaction.oncomplete = () => {
      db.close();
      resolve();
    };

    transaction.onerror = (event) => {
      db.close();
      reject(new Error('删除缩略图失败: ' + event.target.error));
    };
  });
}

/**
 * 清空所有PDF相关数据
 * @returns {Promise<void>}
 */
export async function clearAllPdfData() {
  await transaction(STORES.PDF_FILES, 'readwrite', (store) => {
    return store.clear();
  });

  await transaction(STORES.PDF_PAGES, 'readwrite', (store) => {
    return store.clear();
  });

  await transaction(STORES.THUMBNAILS, 'readwrite', (store) => {
    return store.clear();
  });
}

/**
 * 保存完整的PDF处理结果
 * @param {Object} pdfData - PDF处理后的数据
 * @returns {Promise<string>} - 保存的文件ID
 */
export async function savePdfProcessingResult(pdfData) {
  const fileId = await savePdfFile(pdfData);
  await savePdfPages(fileId, pdfData.pages);
  return fileId;
}