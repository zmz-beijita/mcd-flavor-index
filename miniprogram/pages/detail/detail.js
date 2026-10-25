const store = require('../../utils/flavor-store.js');

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
        item: null,
        voteBtns: [],
        reasonDraft: '',
        submitting: false,
        tip: '',
        myVote: '',
    },

    onLoad(query) {
        const name = decodeURIComponent(query.name || '');
        this.itemName = name;
        store.loadFlavor().then((data) => {
            const raw = (data.items || []).filter(function (it) {
                return it.name === name;
            })[0];
            if (!raw) {
                wx.showToast({ title: '没找到这个商品', icon: 'none' });
                return;
            }
            const avg = raw.avg;
            const cls = avg >= 4.3 ? 'hi' : (avg >= 3.8 ? 'mid' : 'lo');
            const votes = store.getVotes();
            const mine = votes[name] || null;

            const ugc = (raw.ugc || []).map(function (u, i) {
                const c = u.score >= 5 ? 'hi' : (u.score >= 4 ? 'mid' : 'lo');
                return {
                    score: u.score,
                    scoreClass: c,
                    text: u.text,
                    source: u.source,
                    idx: i,
                };
            });

            this.setData({
                item: {
                    name: raw.name,
                    cat: raw.cat,
                    avg: avg.toFixed(1),
                    scoreClass: cls,
                    min: raw.min,
                    max: raw.max,
                    n: raw.n,
                    price: raw.price,
                    tags: raw.official_tags || raw.flavor_tags || [],
                    flavorTags: raw.flavor_tags || [],
                    ingredients: raw.ingredients || [],
                    officialRounds: raw.official_rounds || [],
                    officialDesc: raw.official_desc || '',
                    real: raw.real || [],
                    img: IMAGES[raw.name] || '',
                    rangeLeft: ((raw.min - 2) / 3 * 100).toFixed(1),
                    rangeWidth: (((raw.max - raw.min) / 3) * 100).toFixed(1),
                    markerLeft: (((avg - 2) / 3) * 100).toFixed(1),
                    ugc: ugc,
                },
                myVote: mine ? mine.vote : '',
                reasonDraft: mine ? mine.reason : '',
                voteBtns: this.buildBtns(mine ? mine.vote : ''),
            });
        }).catch(() => {
            wx.showToast({ title: '加载失败', icon: 'none' });
        });
    },

    /* 投票按钮：预先算好高亮 class，避免在 WXML 里做动态键访问 */
    buildBtns(current) {
        return store.VOTE_OPTIONS.map(function (opt) {
            return {
                key: opt.key,
                label: opt.label,
                score: opt.score,
                on: current === opt.key ? 'on ' + opt.key : '',
            };
        });
    },

    doVote(e) {
        const key = e.currentTarget.dataset.key;
        store.saveVote(this.itemName, key, this.data.reasonDraft);
        this.setData({
            myVote: key,
            voteBtns: this.buildBtns(key),
            tip: '',
        });
        // 未写理由时提示一句，但投票已记下
        if (!this.data.reasonDraft.trim()) {
            this.setData({ tip: '票已记上。补一句理由，别人才知道你站哪边' });
        }
    },

    onReason(e) {
        this.setData({ reasonDraft: e.detail.value, tip: '' });
    },

    submitVote() {
        const reason = (this.data.reasonDraft || '').trim();
        if (!reason) {
            this.setData({ tip: '写一句理由才有人看得懂你的票' });
            wx.vibrateShort({ type: 'light' });
            return;
        }
        if (!this.data.myVote) {
            this.setData({ tip: '先选一个「真香 / 一般 / 踩雷」' });
            return;
        }
        this.setData({ submitting: true });
        const res = store.addPost(this.itemName, this.data.myVote, reason);
        if (res.ok) {
            this.setData({ submitting: false, reasonDraft: '', tip: '已发到麦门广场' });
            wx.showToast({ title: '已发到广场', icon: 'success' });
            wx.vibrateShort({ type: 'light' });
        } else {
            this.setData({ submitting: false, tip: res.error || '发送失败' });
        }
    },
});
