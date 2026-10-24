const store = require('../../utils/flavor-store.js');

const LABELS = { good: '真香', mid: '一般', bad: '踩雷' };

Page({
    data: {
        avatarText: '麦',
        votes: [],
    },

    onLoad() {
        this.loadVotes();
    },

    onShow() {
        this.loadVotes();
    },

    loadVotes() {
        const votes = store.getVotes();
        const list = Object.keys(votes).map(function (name) {
            const v = votes[name];
            return {
                name: name,
                vote: v.vote,
                voteLabel: LABELS[v.vote] || '投票',
                reason: v.reason || '',
            };
        });
        this.setData({ votes: list });
    },

    goIndex() {
        wx.switchTab({ url: '/pages/index/index' });
    },
});
