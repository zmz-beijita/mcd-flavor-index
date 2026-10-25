const store = require('../../utils/flavor-store.js');

const IMG_LOCAL={
  "不素之霸双层牛堡": "assets/mcd-brand/cdn-MS_4648_600_1749175329279.png",
  "双层吉士汉堡": "assets/mcd-brand/cdn-MS_1120_600.png",
  "巨无霸": "assets/mcd-brand/cdn-MS_1100_600_1749175370846.png",
  "板烧鸡腿堡": "assets/mcd-brand/cdn-MS_1406_600.png",
  "麦香鱼": "assets/mcd-brand/cdn-MS_1600_600.png",
  "龙焰芝士棒鸡腿堡": "assets/mcd-brand/cdn-MS_521953_600.png",
};


/* 官方商品图映射（来自麦当劳 MCP query-meal-detail 的 image 字段） */
const IMAGES = {
    '龙焰芝士棒鸡腿堡': '/assets/food-521953.png',
    '龙焰鸡腿堡': '/assets/food-521952.png',
    '龙焰芝士棒鸡腿堡三件套': '/assets/food-9900016075.png',
    '龙焰鸡腿堡三件套': '/assets/food-9900016073.png',
    '巨无霸': '/assets/food-1100.png',
    '巨无霸三件套': '/assets/food-9900004064.png',
    '巨无霸四件套': '/assets/food-9900004064.png',
    '板烧鸡腿堡': '/assets/food-1406.png',
    '板烧鸡腿堡三件套': '/assets/food-9900004064.png',
    '板烧鸡腿堡四件套': '/assets/food-9900004064.png',
    '麦辣鸡腿堡': '/assets/food-1440.png',
    '麦辣鸡腿堡三件套': '/assets/food-9900004064.png',
    '麦辣鸡腿堡四件套': '/assets/food-9900004064.png',
    '双层吉士汉堡': '/assets/food-1120.png',
    '双层吉士汉堡四件套': '/assets/food-9900004064.png',
    '麦香鸡': '/assets/food-1450.png',
    '麦香鸡汉堡': '/assets/food-1450.png',
    '麦香鱼': '/assets/food-1600.png',
    '安格斯厚牛堡': '/assets/food-511781.png',
    '不素之霸双层牛堡': '/assets/food-4648.png',
    '麦香鸡中套餐': '/assets/food-9900005453.png',
    '麦香鸡堡': '/assets/food-1450.png',
    '精选单人餐三件套': '/assets/food-9900004064.png',
    '人气经典随心配': '/assets/food-9900013304.png',
    '精选超值随心配': '/assets/food-9900015187.png',
    '中薯条': '/assets/food-4810.png',
    '小杯玉米杯': '/assets/food-4437.png',
    '可乐中杯': '/assets/food-3050.png',
    '无糖可口可乐中杯': '/assets/food-3071.png',
};

function scoreClass(avg) {
    if (avg >= 4.3) return 'hi';
    if (avg >= 3.8) return 'mid';
    return 'lo';
}

Page({
    data: {
        viewState: 'loading',
        items: [],
        hot: [],
        stat: { low: '—', total: 0, all: 0 },
        collectedAt: '',
    },

    onLoad() {
        this.fetchData();
    },

    fetchData() {
        this.setData({ viewState: 'loading' });
        store.loadFlavor().then((data) => {
            const items = (data.items || []).map((it) => {
                const tags = (it.flavor_tags && it.flavor_tags.length)
                    ? it.flavor_tags.slice(0, 2)
                    : (it.ingredients || []).slice(0, 2);
                return {
                    name: it.name,
                    avg: it.avg.toFixed(1),
                    scoreClass: scoreClass(it.avg),
                    n: it.n,
                    min: it.min,
                    max: it.max,
                    spread: it.spread,
                    price: it.price,
                    tags: tags,
                    img: IMG_LOCAL[it.name] || IMAGES[it.name] || it.image || '',
                };
            });
            const hot = (data.hot || []).map((it) => {
                const avg = it.avg;
                return {
                    name: it.name,
                    cat: it.cat,
                    catShort: (it.cat || '').slice(0, 4),
                    price: it.price,
                    tags: (it.flavor_tags || []).slice(0, 2),
                    hasReview: !!it.has_review,
                    avg: avg ? avg.toFixed(1) : '',
                    scoreClass: avg ? scoreClass(avg) : 'none',
                    img: IMG_LOCAL[it.name] || IMAGES[it.name] || it.image || '',
                };
            });
            const total = items.reduce((s, x) => s + x.n, 0);
            let low = items[0];
            items.forEach(function (x) {
                if (parseFloat(x.avg) < parseFloat(low.avg)) low = x;
            });
            this.setData({
                viewState: 'ready',
                items: items,
                hot: hot,
                stat: { low: low ? low.avg : '—', total: total, all: hot.length },
                collectedAt: data.collected_at || '',
            });
        }).catch(() => {
            this.setData({ viewState: 'error' });
        });
    },

    handleRetry() {
        this.fetchData();
    },

    goDetail(e) {
        const name = e.currentTarget.dataset.name;
        wx.navigateTo({ url: '/pages/detail/detail?name=' + encodeURIComponent(name) });
    },
});
