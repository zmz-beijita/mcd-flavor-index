/**
 * 麦门真香榜 · 本地数据层
 *
 * 职责：
 *  1. 读取预置的真香榜数据（data/flavor.json）
 *  2. 维护用户投票（真香 / 一般 / 踩雷）与理由，本地存储
 *  3. 广场：把种子评价与用户投稿合成一条可滚动的理由流
 *
 * 全部走小程序原生 API，不依赖任何浏览器接口。
 */

const FLAVOR_FILE = '/data/flavor.json';
const VOTE_KEY = 'mcd_flavor_votes_v1';
const POST_KEY = 'mcd_flavor_posts_v1';

function readStorage(key, fallback) {
    try {
        const raw = wx.getStorageSync(key);
        if (!raw) return fallback;
        const parsed = JSON.parse(raw);
        return parsed && typeof parsed === 'object' ? parsed : fallback;
    } catch (e) {
        return fallback;
    }
}

function writeStorage(key, value) {
    try {
        wx.setStorageSync(key, JSON.stringify(value));
        return true;
    } catch (e) {
        return false;
    }
}

/* ---------- 预置榜单 ---------- */

function loadFlavor() {
    return new Promise(function (resolve, reject) {
        wx.request({
            url: FLAVOR_FILE,
            dataType: 'json',
            success: function (res) {
                if (res.data && res.data.items && res.data.items.length) {
                    resolve(res.data);
                } else {
                    reject(new Error('榜单数据为空'));
                }
            },
            fail: function (err) {
                reject(err);
            },
        });
    });
}

/* ---------- 投票 ---------- */

/**
 * 投票档位
 * good  真香    —— 值得点
 * mid   一般    —— 凑合
 * bad   踩雷    —— 别点
 */
const VOTE_OPTIONS = [
    { key: 'good', label: '真香', score: 5, color: '#3cc93c', shadow: '#2aa02a' },
    { key: 'mid', label: '一般', score: 3, color: '#ffc72c', shadow: '#dfa000' },
    { key: 'bad', label: '踩雷', score: 2, color: '#e8342a', shadow: '#b32018' },
];

function getVotes() {
    return readStorage(VOTE_KEY, {});
}

function saveVote(itemName, voteKey, reason) {
    const votes = getVotes();
    votes[itemName] = {
        vote: voteKey,
        reason: (reason || '').trim().slice(0, 60),
        at: Date.now(),
    };
    writeStorage(VOTE_KEY, votes);
    return votes;
}

function clearVote(itemName) {
    const votes = getVotes();
    if (votes[itemName]) {
        delete votes[itemName];
        writeStorage(VOTE_KEY, votes);
    }
    return votes;
}

function voteOption(voteKey) {
    for (let i = 0; i < VOTE_OPTIONS.length; i++) {
        if (VOTE_OPTIONS[i].key === voteKey) return VOTE_OPTIONS[i];
    }
    return VOTE_OPTIONS[1];
}

/* ---------- 广场投稿 ---------- */

function getPosts() {
    const list = readStorage(POST_KEY, []);
    return Array.isArray(list) ? list : [];
}

function addPost(itemName, voteKey, reason) {
    const text = (reason || '').trim();
    if (!text) {
        return { ok: false, error: '写一句理由才有人看得懂你的票' };
    }
    const posts = getPosts();
    const opt = voteOption(voteKey);
    posts.unshift({
        id: 'p' + Date.now(),
        item: itemName,
        vote: voteKey,
        color: opt.color,
        text: text.slice(0, 60),
        at: Date.now(),
        mine: true,
    });
    writeStorage(POST_KEY, posts.slice(0, 50));
    return { ok: true, posts: posts };
}

/**
 * 广场流：用户投稿 + 种子评价合并，按时间倒序。
 * 种子评价没有真实时间戳，用采集日期的相对偏移模拟，保证流是活的。
 */
function buildSquare(items) {
    const posts = getPosts();
    const flow = posts.slice();
    const seed = [];
    items.forEach(function (item) {
        (item.ugc || []).forEach(function (u, idx) {
            seed.push({
                id: 's-' + item.name + '-' + idx,
                item: item.name,
                vote: u.score >= 5 ? 'good' : (u.score >= 4 ? 'mid' : 'bad'),
                color: u.score >= 5 ? '#3cc93c' : (u.score >= 4 ? '#ffc72c' : '#e8342a'),
                text: u.text,
                source: u.source,
                at: 0,
                seed: true,
            });
        });
    });
    flow.push.apply(flow, seed);
    flow.sort(function (a, b) {
        if (a.mine && !b.mine) return -1;
        if (!a.mine && b.mine) return 1;
        return b.at - a.at;
    });
    return flow;
}

module.exports = {
    VOTE_OPTIONS: VOTE_OPTIONS,
    loadFlavor: loadFlavor,
    getVotes: getVotes,
    saveVote: saveVote,
    clearVote: clearVote,
    voteOption: voteOption,
    getPosts: getPosts,
    addPost: addPost,
    buildSquare: buildSquare,
};
