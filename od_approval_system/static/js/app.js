document.addEventListener('DOMContentLoaded', () => {
  const overlay = document.getElementById('loadingOverlay');
  const sidebar = document.getElementById('sidebar');
  const toggle = document.getElementById('sidebarToggle');

  if (toggle && sidebar) {
    toggle.addEventListener('click', () => sidebar.classList.toggle('show'));
    document.addEventListener('click', (event) => {
      if (window.innerWidth < 992 && sidebar.classList.contains('show') && !sidebar.contains(event.target) && !toggle.contains(event.target)) {
        sidebar.classList.remove('show');
      }
    });
  }

  const currentPath = window.location.pathname.replace(/\/$/, '');
  document.querySelectorAll('.sidebar .nav-link[href]').forEach(link => {
    const linkPath = new URL(link.href, window.location.origin).pathname.replace(/\/$/, '');
    if (linkPath && (currentPath === linkPath || currentPath.startsWith(linkPath + '/'))) {
      link.classList.add('active');
    }
  });

  document.querySelectorAll('form.needs-loader').forEach(form => {
    form.addEventListener('submit', () => {
      const btn = form.querySelector('button[type="submit"],button:not([type])');
      if (btn) {
        btn.disabled = true;
        btn.dataset.originalText = btn.innerText;
        btn.innerText = 'Processing...';
      }
      if (overlay) overlay.classList.add('show');
    });
  });

  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', (e) => {
      if (!confirm(el.dataset.confirm || 'Are you sure?')) e.preventDefault();
    });
  });

  document.querySelectorAll('.alert').forEach(alert => {
    setTimeout(() => {
      if (window.bootstrap) {
        const instance = bootstrap.Alert.getOrCreateInstance(alert);
        instance.close();
      }
    }, 6500);
  });
});

// OpenRouter-powered OD Assistant widget
(function(){
  function getCookie(name){
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if(parts.length === 2) return parts.pop().split(';').shift();
    return '';
  }
  function addMsg(box, text, who){
    const div=document.createElement('div');
    div.className='ai-msg '+who;
    div.textContent=text;
    box.appendChild(div);
    box.scrollTop=box.scrollHeight;
  }
  document.addEventListener('DOMContentLoaded',()=>{
    const launcher=document.getElementById('aiChatLauncher');
    const panel=document.getElementById('aiChatPanel');
    const close=document.getElementById('aiChatClose');
    const form=document.getElementById('aiChatForm');
    const input=document.getElementById('aiChatInput');
    const messages=document.getElementById('aiChatMessages');
    if(!launcher||!panel||!form||!input||!messages) return;
    launcher.addEventListener('click',()=>panel.classList.toggle('show'));
    if(close) close.addEventListener('click',()=>panel.classList.remove('show'));
    form.addEventListener('submit',async(e)=>{
      e.preventDefault();
      const text=input.value.trim();
      if(!text) return;
      addMsg(messages,text,'user');
      input.value='';
      const pending=document.createElement('div');
      pending.className='ai-msg bot'; pending.textContent='Thinking...'; messages.appendChild(pending); messages.scrollTop=messages.scrollHeight;
      try{
        const res=await fetch('/chatbot/ask/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':getCookie('csrftoken')},body:JSON.stringify({message:text})});
        const data=await res.json();
        pending.textContent=data.reply || 'No response.';
      }catch(err){
        pending.textContent='Assistant connection failed. Check your OpenRouter API key and internet connection.';
      }
    });
  });
})();
