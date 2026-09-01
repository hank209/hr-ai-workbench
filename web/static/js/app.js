/* 人事工作台前端脚本：一键复制 + 回复过滤 + 知识检索 */
/* 侧边栏抽屉（移动端 / 窄屏） */
function toggleSidebar() {
  var sb = document.getElementById('sidebar');
  var ov = document.getElementById('sidebarOverlay');
  if (!sb) return;
  var open = sb.classList.toggle('open');
  if (ov) ov.classList.toggle('show', open);
}
function closeSidebar() {
  var sb = document.getElementById('sidebar');
  var ov = document.getElementById('sidebarOverlay');
  if (sb) sb.classList.remove('open');
  if (ov) ov.classList.remove('show');
}
/* 点击导航项后自动收起抽屉（窄屏） */
document.addEventListener('click', function (e) {
  var item = e.target.closest ? e.target.closest('.nav-item') : null;
  if (item) closeSidebar();
});

function copyText(text, replyId) {
  var done = function () {
    toast('已复制，可直接粘贴发送');
    if (replyId) {
      fetch('/api/reply/' + replyId + '/copy', { method: 'POST' });
    }
  };
  if (navigator.clipboard && window.isSecureContext === false) {
    /* 本地 http 环境：clipboard API 受限，走降级 */
  }
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(done, function () { legacyCopy(text); done(); });
  } else {
    legacyCopy(text);
    done();
  }
}
function legacyCopy(text) {
  var ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  try { document.execCommand('copy'); } catch (e) {}
  document.body.removeChild(ta);
}
function toast(msg) {
  var el = document.createElement('div');
  el.className = 'toast';
  el.textContent = msg;
  document.body.appendChild(el);
  requestAnimationFrame(function () { el.classList.add('show'); });
  setTimeout(function () { el.classList.remove('show'); setTimeout(function () { el.remove(); }, 300); }, 1600);
}
/* 常用回复：分类过滤 + 关键词搜索（纯前端） */
function filterReplies(cat) {
  var q = (document.getElementById('replySearch') || {}).value || '';
  document.querySelectorAll('.reply-card').forEach(function (card) {
    var okCat = !cat || card.dataset.cat === cat || cat === '全部';
    var okQ = !q || (card.dataset.title + ' ' + card.dataset.kw + ' ' + card.dataset.content).toLowerCase().indexOf(q.toLowerCase()) >= 0;
    card.style.display = (okCat && okQ) ? '' : 'none';
  });
}
/* 知识库检索 */
function searchKnowledge() {
  var q = (document.getElementById('kwSearch') || {}).value;
  var box = document.getElementById('searchResult');
  if (!q || !box) return;
  box.innerHTML = '<div class="empty">检索中…</div>';
  var fd = new FormData();
  fd.append('q', q);
  fd.append('limit', '10');
  fetch('/api/knowledge/search', { method: 'POST', body: fd })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (!data.items || !data.items.length) {
        box.innerHTML = '<div class="empty">未检索到相关内容，换个关键词试试，或确认文档已上传入库。</div>';
        return;
      }
      var html = data.items.map(function (it) {
        return '<div class="search-result-item">' +
               '<div class="sr-src">' + esc(it.title + (it.section ? ' · ' + it.section : '') +
               (it.version ? '（' + it.version + '）' : '') +
               (it.effective_date ? ' · 生效' + it.effective_date : '')) + '</div>' +
               '<div class="sr-body">' + esc(it.content) + '</div></div>';
      }).join('');
      box.innerHTML = html;
    })
    .catch(function () {
      box.innerHTML = '<div class="empty">检索失败，请重试。</div>';
    });
}
function esc(s) {
  var d = document.createElement('div');
  d.textContent = s || '';
  return d.innerHTML;
}
/* 面试列表：状态筛选 */
function filterInterviews(status) {
  document.querySelectorAll('#interviewRows tr').forEach(function (tr) {
    var st = tr.dataset.status;
    tr.style.display = (!status || status === '全部' || st === status) ? '' : 'none';
  });
}
