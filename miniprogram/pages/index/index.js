const store = require('../../utils/flavor-store.js');

/* 官方商品图映射（来自麦当劳 MCP query-meal-detail 的 image 字段） */
const IMAGES = {
    '龙焰芝士棒鸡腿堡': '/assets/food-521953.png',
    '巨无霸': '/assets/food-1100.png',
    '板烧鸡腿堡': '/assets/food-1406.png',
    '麦辣鸡腿堡': '/assets/food-1440.png',
    '双层吉士汉堡': '/assets/food-1120.png',
    '麦香鸡汉堡': '/assets/food-9900005453.png',
};

Page({
    data: {
        viewState: 'loading',
        items: [],
        stat: { low: '—', total: 0, items: 0 },
        collectedAt: '',
    },

    onLoad() {
        this.fetchData();
    },

    fetchData() {
        this.setData({ viewState: 'loading' });
        store.loadFlavor().then((data) => {
            const items = (data.items || []).map((it) => {
                const avg = it.avg;
                const scoreClass = avg >= 4.3 ? 'hi' : (avg >= 3.8 ? 'mid' : 'lo');
                return {
                    name: it.name,
                    avg: avg.toFixed(1),
                    n: it.n,
                    min: it.min,
                    max: it.max,
                    spread: it.spread,
                    price: it.price,
                    tags: (it.tags || []).slice(0, 2),
                    realText: (it.real || []).join(' · '),
                    img: IMAGES[it.name] || '',
                    scoreClass: scoreClass,
                };
            });
            const total = items.reduce((s, it) => s + it.n, 0);
            let low = items[0];
            items.forEach(function (it) {
                if (parseFloat(it.avg) < parseFloat(low.avg)) low = it;
            });
            this.setData({
                viewState: 'ready',
                items: items,
                stat: {
                    low: low ? low.avg : '—',
                    total: total,
                    items: items.length,
                },
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
