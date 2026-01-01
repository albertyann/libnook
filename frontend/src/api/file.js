import request from "./request";

export const Api = {
    // 获取tabs list
    ocr(fileId, page, data) {
        return request(`/api/file/${fileId}/ocr/${page}`,
            'post', data
        )
    },
    noOcr(fileId, page, data) {
        return request(`/api/file/${fileId}/noocr/${page}`,
            'post', data
        )
    },
    info(fileId) {
        return request(`/api/file/${fileId}/info`,
            'get'
        )
    },
    saveContent(fileId, page, data) {
        return request(`/api/file/content/${fileId}`,
            'post', data
        )
    }
}

export default Api