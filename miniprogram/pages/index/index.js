const store = require('../../utils/flavor-store.js');

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
                    img: it.local_image || '',
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
                    img: it.local_image || '',
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
