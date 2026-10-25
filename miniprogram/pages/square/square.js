const store = require('../../utils/flavor-store.js');

const LABELS = { good: '真香', mid: '一般', bad: '踩雷' };

Page({
    data: {
        flow: [],
        filter: 'all',
        // 就地发帖
        itemNames: [],
        itemIndex: 0,
        pickName: '',
        vote: 'good',
        reason: '',
        tip: '',
        tipOk: false,
    },

    onLoad() {
        this.loadData();
    },

    onShow() {
        this.loadData();
    },

    loadData() {
        store.loadFlavor().then((data) => {
            const items = data.items || [];

            // 下拉可选商品
            const names = items.map(function (it) { return it.name; });
            const itemIndex = Math.min(this.data.itemIndex, Math.max(0, names.length - 1));
            this.setData({
                itemNames: names,
                itemIndex: itemIndex,
                pickName: names[itemIndex] || '',
            });

            const all = store.buildSquare(items);
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

    onPickItem(e) {
        const idx = Number(e.detail.value);
        this.setData({
            itemIndex: idx,
            pickName: this.data.itemNames[idx] || '',
        });
    },

    onPickVote(e) {
        this.setData({ vote: e.currentTarget.dataset.v });
    },

    onReason(e) {
        this.setData({ reason: e.detail.value });
    },

    submitPost() {
        const name = this.data.pickName;
        const reason = (this.data.reason || '').trim();
        if (!name) {
            this.setData({ tip: '先选一个商品', tipOk: false });
            return;
        }
        if (!reason) {
            this.setData({ tip: '写一句理由才有人看得懂你的票', tipOk: false });
            return;
        }
        const res = store.addPost(name, this.data.vote, reason);
        if (!res.ok) {
            this.setData({ tip: res.error || '投稿失败', tipOk: false });
            return;
        }
        // 同步一份投票记录，详情页能看到「你投过」
        store.saveVote(name, this.data.vote, reason);
        this.setData({ reason: '', tip: '已发到麦门广场', tipOk: true });
        this.loadData();
    },

    goIndex() {
        wx.switchTab({ url: '/pages/index/index' });
    },
});
