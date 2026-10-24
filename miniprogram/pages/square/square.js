const store = require('../../utils/flavor-store.js');

const LABELS = { good: '真香', mid: '一般', bad: '踩雷' };

Page({
    data: {
        flow: [],
        filter: 'all',
    },

    onLoad() {
        this.loadData();
    },

    onShow() {
        this.loadData();
    },

    loadData() {
        store.loadFlavor().then((data) => {
            const all = store.buildSquare(data.items || []);
            const flow = all.map(function (p) {
                return {
                    id: p.id,
                    vote: p.vote,
                    voteLabel: LABELS[p.vote] || '投票',
                    item: p.item,
                    text: p.text,
                    source: p.source || '',
                    mine: !!p.mine,
                    n: 0,
                };
            });
            this.setData({ flow: this.applyFilter(flow) });
        }).catch(() => {
            this.setData({ flow: [] });
        });
    },

    applyFilter(flow) {
        if (this.data.filter === 'all') return flow;
        return flow.filter(function (p) {
            return p.vote === this.data.filter;
        }, this);
    },

    setFilter(e) {
        const f = e.currentTarget.dataset.f;
        this.setData({ filter: f });
        this.loadData();
    },

    goIndex() {
        wx.switchTab({ url: '/pages/index/index' });
    },
});
