import axios from "axios";

// 该地址通过 Vite 的环境变量注入，需在项目根目录下的 .env 或 .env.* 文件中配置 VITE_APP_BASE_API
const baseURL = import.meta.env.VITE_APP_BASE_API;

// 前端跨域传递Cookie设置
const service = axios.create({
    withCredentials: true,
    baseURL
})

// 在请求时在请求参数上统一添加参数
service.interceptors.request.use(
    config => {
        return config
    },
    error => Promise.reject(error) 
)

const state = {
    401: function LoadToLogin() {
        window.location.href = '/login' // 重定向登录页面
    }
}

// 添加一个响应拦截器
service.interceptors.response.use(
    res => {
        return Promise.resolve(res.data)
    },
    err => {
        if(state[err.response.status]) {
            state[err.response.status]()
        }
        return Promise.reject(err)
    }
)

const request = (url, methods, data, options = {}) => {
    const query = {
        url: url,
        method: methods,
        data: data,
        headers: Object.assign(options)
    }
    return service(query)
}

export default request