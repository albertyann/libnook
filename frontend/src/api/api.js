import request from "./request";

export const Api = {
    // 获取tabs list
    loadFiles(data) {
        return request(`/api/pdf/files`,
            'get'
        )
    }
}