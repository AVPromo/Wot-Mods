/* GRZ Session Stats — no frameworks, no network calls, no demonstration data. */
(function () {
    'use strict';
    var root = document.getElementById('grz-session-stats');
    if (!root) { return; }

    var state = { scope: 'launch', group: 'vehicles', xp: 'base', payload: null,
        dialog: false, bound: false, connecting: false, callbackId: null, callbackRegistering: false, actionError: null,
        nativeWidth: 0, nativeHeight: 0, nativeScale: 1, diagnostics: {}, dragging: false,
        scrollSpeed: 1, appearanceNode: null, appearanceCSS: '', destroyed: false,
        list: [], loadedCount: 40, renderedCount: 0 };
    var nodes = {};
    var ids = ['started', 'summary', 'groups', 'scroll', 'status', 'reset',
        'reset-overlay', 'reset-cancel', 'reset-confirm', 'close', 'refresh',
        'group-tabs', 'list-meta', 'titlebar'];
    var i;
    for (i = 0; i < ids.length; i += 1) { nodes[ids[i]] = document.getElementById('ss-' + ids[i]); }

    function element(tag, className, value) {
        var result = document.createElement(tag);
        if (className) { result.className = className; }
        if (value !== undefined && value !== null) { result.textContent = String(value); }
        return result;
    }
    function append(parent, child) { parent.appendChild(child); return child; }
    function clear(node) { while (node.firstChild) { node.removeChild(node.firstChild); } }
    function hasNumber(value) { return typeof value === 'number' && isFinite(value); }
    function integer(value) { return hasNumber(value) ? String(Math.round(value)) : '—'; }
    function number(value) {
        if (!hasNumber(value)) { return '—'; }
        return String(Math.round(value)).replace(/\B(?=(\d{3})+(?!\d))/g, '\u00a0');
    }
    function signed(value) {
        if (!hasNumber(value)) { return '—'; }
        return value > 0 ? '+' + number(value) : (value < 0 ? '-' + number(-value) : '0');
    }
    function cost(value) {
        if (!hasNumber(value)) { return '—'; }
        return value === 0 ? '0' : '-' + number(Math.abs(value));
    }
    function rate(value) { return hasNumber(value) ? value.toFixed(1).replace('.', ',') + '%' : '—'; }
    function pad(value) { return value < 10 ? '0' + value : String(value); }
    function date(value, shortDate) {
        if (!hasNumber(value)) { return '—'; }
        var d = new Date(value * 1000);
        if (!isFinite(d.getTime())) { return '—'; }
        return pad(d.getDate()) + '.' + pad(d.getMonth() + 1) +
            (shortDate ? '' : '.' + d.getFullYear()) + ', ' + pad(d.getHours()) + ':' + pad(d.getMinutes());
    }
    function unwrap(value) {
        if (value && typeof value === 'object' && value.value !== undefined) { return value.value; }
        return value;
    }
    function appearanceFailure() {
        if (state.diagnostics.appearance) { return; }
        state.diagnostics.appearance = true;
        try {
            if (window.console && typeof window.console.warn === 'function') {
                window.console.warn('GRZ Session Stats: appearance bridge unavailable; using stylesheet defaults.');
            }
        } catch (ignored) { /* A cosmetic failure must not interrupt statistics. */ }
    }
    function clearAppearance() {
        try {
            if (state.appearanceNode && state.appearanceNode.parentNode) {
                state.appearanceNode.parentNode.removeChild(state.appearanceNode);
            }
        } catch (error) {
            try { state.appearanceNode.textContent = ''; } catch (ignored) { /* Native DOM may be gone. */ }
            appearanceFailure();
        }
        state.appearanceNode = null;
        state.appearanceCSS = '';
    }
    function applyAppearance(raw) {
        state.scrollSpeed = 1;
        try {
            var value = unwrap(raw);
            if (value === undefined || value === null) { clearAppearance(); return; }
            if (typeof value !== 'object' || Array.isArray(value)) { throw new Error('appearance shape'); }
            var speed = unwrap(value.scroll_speed);
            if (speed !== undefined && speed !== null) {
                if (hasNumber(speed) && speed >= 0.1 && speed <= 8) { state.scrollSpeed = speed; }
                else { appearanceFailure(); }
            }
            // Python accepts only the documented colour/number fields and
            // compiles these declarations. No user CSS or markup is evaluated.
            var css = unwrap(value.panel_css);
            if (css === undefined || css === null || css === '') { clearAppearance(); return; }
            if (typeof css !== 'string' || css.length > 65536 || css.indexOf('\u0000') !== -1 || css.indexOf('<') !== -1) {
                throw new Error('appearance CSS shape');
            }
            if (css === state.appearanceCSS && state.appearanceNode && state.appearanceNode.parentNode) { return; }
            if (!state.appearanceNode || !state.appearanceNode.parentNode) {
                state.appearanceNode = document.createElement('style');
                state.appearanceNode.id = 'grz-session-stats-appearance';
                document.head.appendChild(state.appearanceNode);
            }
            state.appearanceNode.textContent = css;
            state.appearanceCSS = css;
        } catch (error) {
            clearAppearance();
            appearanceFailure();
        }
    }
    function series(value) {
        return value || { min: null, avg: null, max: null, sum: null, count: 0 };
    }
    function coverage(count, total) {
        return hasNumber(count) && count < total ? String(count) + '/' + String(total) : '';
    }
    function observedTotal(stats) {
        return hasNumber(stats.observed_battles) && stats.observed_battles >= (stats.battles || 0) ?
            stats.observed_battles : (stats.battles || 0);
    }
    function battleCount(stats) {
        var total = observedTotal(stats);
        return number(stats.battles) + (total > (stats.battles || 0) ? ' / ' + number(total) : '');
    }
    function selected(id, active) {
        var button = document.getElementById(id);
        button.className = button.className.replace(/\s*is-active/g, '') + (active ? ' is-active' : '');
        button.setAttribute('aria-pressed', active ? 'true' : 'false');
    }
    function quantityClass(value) {
        return !hasNumber(value) ? ' ss-unknown' : (value > 0 ? ' ss-positive' : (value < 0 ? ' ss-negative' : ''));
    }
    function headlineStat(parent, label, value, wn8, compact) {
        var holder = append(parent, element('div', compact ? 'ss-group-kpi' : 'ss-kpi'));
        append(holder, element('span', 'ss-kpi-label', label));
        append(holder, element('strong', 'ss-kpi-value' + (wn8 ? ' ss-wn8' : ''), value));
    }
    function measureRow(parent, label, data, wn8, total) {
        var row = append(parent, element('div', 'ss-metric-row'));
        var name = append(row, element('div', 'ss-metric-name'));
        append(name, element('span', 'ss-cell-value', label));
        var partial = coverage(data.count, total);
        if (partial) { append(name, element('span', 'ss-cell-coverage', partial + ' bitew')); }
        append(row, element('div', 'ss-metric-number', wn8 ? integer(data.min) : number(data.min)));
        append(row, element('div', 'ss-metric-number', wn8 ? integer(data.avg) : number(data.avg)));
        append(row, element('div', 'ss-metric-number', wn8 ? integer(data.max) : number(data.max)));
    }
    function battleMeasure(parent, label, value, wn8) {
        var row = append(parent, element('div', 'ss-battle-measure'));
        append(row, element('span', 'ss-battle-label', label));
        append(row, element('strong', 'ss-battle-value' + (wn8 ? ' ss-wn8' : ''),
            wn8 ? integer(value) : number(value)));
    }
    function moneyCell(parent, data, field, total) {
        var value = data[field];
        var output = field === 'costs' ? cost(value) : (field === 'net' ? signed(value) : number(value));
        var cell = append(parent, element('div', 'ss-money-value' +
            (field === 'net' ? quantityClass(value) : (!hasNumber(value) ? ' ss-unknown' : ''))));
        append(cell, element('span', 'ss-cell-value', output));
        var partial = coverage(data[field + '_count'], total);
        if (partial) { append(cell, element('span', 'ss-cell-coverage', partial)); }
    }
    function moneyRow(parent, name, data, total) {
        data = data || {};
        var row = append(parent, element('div', 'ss-money-row'));
        append(row, element('div', 'ss-money-label', name));
        moneyCell(row, data, 'income', total);
        moneyCell(row, data, 'costs', total);
        moneyCell(row, data, 'net', total);
    }
    function details(parent, stats, global, battle) {
        stats = stats || {};
        var total = observedTotal(stats);
        var holder = append(parent, element('div', 'ss-details' + (battle ? ' ss-battle-details' : '')));
        var performance = append(holder, element('div', 'ss-performance' + (battle ? ' ss-battle-performance' : '')));
        append(performance, element('h3', 'ss-detail-title', battle ? 'Wynik bitwy' : 'Skuteczność bojowa'));
        var xpLabel = state.xp === 'base' ? 'Bazowe PD' : 'Otrzymane PD';
        var xp = series(state.xp === 'base' ? stats.xp_base : stats.xp_received);
        if (battle) {
            /* A battle row represents one result, not a distribution. Check
               coverage so a missing value cannot become a plausible zero. */
            battleMeasure(performance, xpLabel, xp.count === 1 ? xp.sum : null, false);
            battleMeasure(performance, 'WN8', stats.wn8_count === 1 ? stats.wn8 : null, true);
        } else {
            var header = append(performance, element('div', 'ss-metric-head'));
            append(header, element('div', 'ss-metric-name', ''));
            append(header, element('div', 'ss-metric-number', 'Min'));
            append(header, element('div', 'ss-metric-number', 'Średnia'));
            append(header, element('div', 'ss-metric-number', 'Max'));
            measureRow(performance, xpLabel, xp, false, total);
            measureRow(performance, 'WN8 bitew', series(stats.battle_wn8), true, total);
        }
        var free = append(performance, element('div', 'ss-free-xp'));
        append(free, element('span', '', 'Wolne PD:'));
        append(free, element('strong', '', number(series(stats.free_xp).sum)));
        var partialFree = coverage(series(stats.free_xp).count, total);
        if (partialFree) { append(free, element('span', '', ' (' + partialFree + ' bitew)')); }
        if (global) {
            append(performance, element('div', 'ss-explainer',
                'Średnia WN8 bitew może różnić się od WN8 zakresu.'));
        }
        var economy = append(holder, element('div', 'ss-economy'));
        append(economy, element('h3', 'ss-detail-title', battle ? 'Finanse bitwy' : 'Finanse z bitew'));
        var moneyHeader = append(economy, element('div', 'ss-money-head'));
        append(moneyHeader, element('div', 'ss-money-label', 'Waluta'));
        append(moneyHeader, element('div', 'ss-money-value', 'Przychód'));
        append(moneyHeader, element('div', 'ss-money-value', 'Koszty'));
        append(moneyHeader, element('div', 'ss-money-value', 'Netto'));
        var currencies = stats.currencies || {};
        moneyRow(economy, 'Kredyty', currencies.credits, total);
        moneyRow(economy, 'Obligacje', currencies.bonds, total);
        var gold = currencies.gold || {};
        if ((hasNumber(gold.income) && gold.income !== 0) ||
                (hasNumber(gold.costs) && gold.costs !== 0) ||
                (hasNumber(gold.net) && gold.net !== 0)) {
            moneyRow(economy, 'Złoto', gold, total);
        }
        if (global) {
            append(economy, element('div', 'ss-explainer',
                'Koszty obejmują rozliczone wydatki związane z bitwami.'));
        }
        var wnPartial = coverage(stats.wn8_count, total);
        if (wnPartial) {
            append(parent, element('div', 'ss-coverage-note',
                battle ? 'Brak danych do obliczenia WN8 tej bitwy.' :
                    'WN8 zakresu: dane dla ' + wnPartial + ' bitew.'));
        }
    }
    function renderSummary(stats, scope) {
        clear(nodes.summary);
        var headline = append(nodes.summary, element('div', 'ss-headline'));
        var missing = observedTotal(stats) > (stats.battles || 0);
        headlineStat(headline, missing ? 'Bitwy z wynikiem' : 'Bitwy', battleCount(stats), false, false);
        headlineStat(headline, missing ? 'Win rate*' : 'Win rate', rate(stats.win_rate), false, false);
        headlineStat(headline, 'WN8 zakresu', integer(stats.wn8), true, false);
        var outcomes = append(nodes.summary, element('p', 'ss-outcomes'));
        append(outcomes, element('span', '', 'Zwycięstwa '));
        append(outcomes, element('strong', '', number(stats.wins)));
        append(outcomes, element('span', '', '  ·  Porażki '));
        append(outcomes, element('strong', '', number(stats.losses)));
        append(outcomes, element('span', '', '  ·  Remisy '));
        append(outcomes, element('strong', '', number(stats.draws)));
        if (scope.pending > 0) {
            append(outcomes, element('span', '', '  ·  Oczekujące: ' + number(scope.pending)));
        }
        if (missing) {
            append(nodes.summary, element('p', 'ss-data-notice',
                'Niepełne statystyki: wyniki ' + number(stats.battles) + ' z ' + number(observedTotal(stats)) +
                ' zarejestrowanych bitew. Procenty, średnie i sumy dotyczą odebranych danych.'));
        } else if (stats.partial_results > 0) {
            append(nodes.summary, element('p', 'ss-data-notice',
                'Niepełne dane w ' + number(stats.partial_results) + ' wynikach. Braki są oznaczone przy poszczególnych statystykach.'));
        }
        details(nodes.summary, stats, true);
    }
    function tierText(tier) {
        return ['','I','II','III','IV','V','VI','VII','VIII','IX','X','XI'][tier] || '';
    }
    function vehicleType(type) {
        var labels = { lightTank:'Czołg lekki', mediumTank:'Czołg średni', heavyTank:'Czołg ciężki',
            AT_SPG:'Niszczyciel czołgów', SPG:'Działo samobieżne' };
        return labels[type] || '';
    }
    function battleOutcome(outcome) {
        return { win:'Zwycięstwo', loss:'Porażka', draw:'Remis' }[outcome] || 'Nieznany wynik';
    }
    function ordered(items) {
        var copy = items.slice(0);
        copy.sort(function (a, b) {
            if (state.group === 'battles') { return (b.started_at || 0) - (a.started_at || 0); }
            var countDifference = ((b.stats || {}).battles || 0) - ((a.stats || {}).battles || 0);
            if (countDifference) { return countDifference; }
            var left = String(a.name || ''), right = String(b.name || '');
            return left < right ? -1 : (left > right ? 1 : 0);
        });
        return copy;
    }
    function appendVisual(parent, item) {
        var visual = item.visual;
        if (!visual || (visual.kind !== 'vehicle' && visual.kind !== 'map')) { return; }
        var src = visual.src;
        var prefix = visual.kind === 'vehicle' ? 'img://gui/maps/icons/vehicle/' : 'img://gui/maps/icons/map/';
        /* URLs come from the native R/backport resolver, which checks ResMgr.isFile.
           UI accepts only these local asset families; no remote URLs or CSS escapes. */
        if (typeof src !== 'string' || src.indexOf(prefix) !== 0 || src.length <= prefix.length ||
                src.indexOf('..') !== -1 || /[^A-Za-z0-9_./:-]/.test(src)) { return; }
        var thumb = append(parent, element('div', 'ss-group-thumb'));
        thumb.setAttribute('role', 'img');
        thumb.setAttribute('aria-label', String(visual.alt || item.name || ''));
        /* Background contain is supported by Gameface; object-fit is not. */
        thumb.style.backgroundImage = 'url("' + src + '")';
    }
    function appendGroupBatch(limit) {
        var list = state.list;
        var end = Math.min(list.length, limit);
        var fragment = document.createDocumentFragment();
        var index, item, stats, group, header, identity, subtitle, outcome;
        var battle = state.group === 'battles';
        for (index = state.renderedCount; index < end; index += 1) {
            item = list[index];
            stats = item.stats || {};
            group = append(fragment, element('div', 'ss-group' + (battle ? ' ss-battle' : '')));
            group.setAttribute('role', 'group');
            group.setAttribute('data-group-id', String(item.id || ''));
            header = append(group, element('div', 'ss-group-header'));
            appendVisual(header, item);
            identity = append(header, element('div', 'ss-group-name'));
            append(identity, element('h2', 'ss-group-title', item.name || 'Nieznany'));
            subtitle = state.group === 'vehicles' ?
                (tierText(item.tier) + (vehicleType(item.type) ? ' · ' + vehicleType(item.type) : '')) :
                (battle ? date(item.started_at, true) + ' · ' + (item.map || 'Nieznana mapa') : '');
            if (subtitle) { append(identity, element('div', 'ss-group-subtitle', subtitle)); }
            if (battle) {
                outcome = {win: 'win', loss: 'loss', draw: 'draw'}[item.outcome] || 'unknown';
                append(header, element('span', 'ss-battle-outcome ss-outcome-' + outcome, battleOutcome(item.outcome)));
            } else {
                headlineStat(header, 'Bitwy', battleCount(stats), false, true);
                headlineStat(header, 'Win rate', rate(stats.win_rate), false, true);
                headlineStat(header, 'WN8', integer(stats.wn8), true, true);
            }
            details(group, stats, false, battle);
        }
        nodes.groups.appendChild(fragment);
        state.renderedCount = end;
        state.loadedCount = Math.max(40, end);
    }
    function renderGroups(scope) {
        clear(nodes.groups);
        var labels = {vehicles:'czołgów', maps:'map', battles:'bitew'};
        state.list = ordered(scope[state.group] || []);
        state.renderedCount = 0;
        nodes.groups.setAttribute('aria-label', 'Wyniki według ' + labels[state.group]);
        nodes['list-meta'].textContent = number(state.list.length) + ' ' + labels[state.group] +
            (state.group === 'battles' ? ' · od najnowszej' : ' · najwięcej bitew na początku');
        if (!state.list.length) {
            append(nodes.groups, element('p', 'ss-empty',
                'Brak rozliczonych bitew w tym zakresie. Wyniki pojawią się po zakończeniu bitwy.'));
            return;
        }
        appendGroupBatch(state.loadedCount);
    }
    function loadNearBottom() {
        if (state.renderedCount >= state.list.length) { return; }
        var remaining = nodes.scroll.scrollHeight - nodes.scroll.scrollTop - nodes.scroll.clientHeight;
        if (remaining <= 200) { appendGroupBatch(state.renderedCount + 40); }
    }
    function onNativeWheel(event) {
        /* WoT's vertical-scroll adapter treats positive deltaY as up (Next=-1).
           A browser's default overflow scroll uses the opposite sign. Only the
           bound Gameface document needs this adapter; the HTML preview keeps
           the browser's own wheel/trackpad handling. See WHEEL_0.2.4_SOURCE_EVIDENCE. */
        /* Do not add manual movement to a default action we cannot cancel. */
        if (!state.bound || !event || event.defaultPrevented || event.cancelable === false) { return; }
        if (state.dialog) {
            event.preventDefault();
            event.stopPropagation();
            return;
        }
        var target = event.target;
        while (target && target !== nodes.scroll && target !== root) { target = target.parentNode; }
        if (target !== nodes.scroll) { return; }
        var vertical = event.deltaY;
        var horizontal = hasNumber(event.deltaX) ? event.deltaX : 0;
        if (!hasNumber(vertical)) { return; }
        /* This panel has one vertical list. Do not turn a horizontal gesture
           into vertical movement or let its smaller Y component scroll it. */
        if (event.shiftKey || (horizontal !== 0 && Math.abs(horizontal) >= Math.abs(vertical))) {
            event.preventDefault();
            event.stopPropagation();
            return;
        }
        if (vertical === 0) { return; }
        event.preventDefault();
        event.stopPropagation();
        /* Gameface may report a normalized wheel delta such as +/-1, not a
           browser pixel distance. WoT's own vertical list uses its visible
           height / 4 per wheel event. Use that same proportional step so the
           list remains usable regardless of the device's delta magnitude or
           the client's UI scale. Explicit page-mode input keeps page units. */
        var step = (vertical < 0 ? 1 : -1) * nodes.scroll.clientHeight / 4;
        if (event.deltaMode === 2) { step = -vertical * nodes.scroll.clientHeight; }
        step *= state.scrollSpeed;
        var last = Math.max(0, nodes.scroll.scrollHeight - nodes.scroll.clientHeight);
        nodes.scroll.scrollTop = Math.max(0, Math.min(last, nodes.scroll.scrollTop + step));
        /* Some client revisions deliver programmatic scroll events later.
           Appending near the end must not depend on another wheel notch. */
        loadNearBottom();
    }
    function setStatus(message) { nodes.status.textContent = message; }
    function render() {
        var payload = state.payload;
        if (!payload || !payload.scopes) { return; }
        var hasInstance = !!payload.scopes.instance;
        if (state.scope === 'instance' && !hasInstance) { state.scope = 'manual'; showReset(false); }
        var scopeNames = ['launch', 'manual', 'instance'], scopeIndex;
        for (scopeIndex = 0; scopeIndex < scopeNames.length; scopeIndex += 1) {
            var scopeButton = document.getElementById('ss-scope-' + scopeNames[scopeIndex]);
            scopeButton.style.width = hasInstance ? (scopeNames[scopeIndex] === 'instance' ? '40%' : '30%') : '50%';
            if (scopeNames[scopeIndex] === 'instance') { scopeButton.style.display = hasInstance ? 'flex' : 'none'; }
        }
        document.getElementById('ss-scope-launch').querySelector('.ss-control-label').textContent =
            hasInstance ? 'Od startu' : 'Od uruchomienia';
        var scope = payload.scopes[state.scope];
        if (!scope || !scope.summary) { return; }
        var oldTop = nodes.scroll.scrollTop;
        selected('ss-scope-launch', state.scope === 'launch');
        selected('ss-scope-manual', state.scope === 'manual');
        selected('ss-scope-instance', state.scope === 'instance');
        selected('ss-xp-base', state.xp === 'base');
        selected('ss-xp-received', state.xp === 'received');
        selected('ss-group-vehicles', state.group === 'vehicles');
        selected('ss-group-maps', state.group === 'maps');
        selected('ss-group-battles', state.group === 'battles');
        nodes.started.textContent = (state.scope === 'instance' ? 'Wszystkie konta · Od ' : 'Od ') + date(scope.started_at, false);
        nodes.reset.style.display = state.scope !== 'launch' ? 'flex' : 'none';
        nodes.reset.disabled = state.scope === 'launch';
        renderSummary(scope.summary, scope);
        if (payload.warnings && payload.warnings.length) {
            var notices = append(nodes.summary, element('div', 'ss-data-notices'));
            var warningIndex;
            for (warningIndex = 0; warningIndex < payload.warnings.length; warningIndex += 1) {
                append(notices, element('p', 'ss-data-notice', payload.warnings[warningIndex]));
            }
        }
        renderGroups(scope);
        var text = number(scope.summary.battles) + ' rozliczonych bitew';
        if (observedTotal(scope.summary) > (scope.summary.battles || 0)) {
            text = 'Niepełne dane: wyniki ' + number(scope.summary.battles) + ' / ' + number(observedTotal(scope.summary));
        }
        if (scope.pending > 0) { text += ' · ' + number(scope.pending) + ' oczekujących'; }
        if (payload.warnings && payload.warnings.length) { text += ' · Uwagi do danych: ' + payload.warnings.length; }
        setStatus(state.actionError || text);
        nodes.scroll.scrollTop = oldTop;
    }
    function update(payload) {
        if (state.destroyed) { return false; }
        try {
            var value = unwrap(payload);
            if (typeof value === 'string') { value = JSON.parse(value); }
            if (!value || typeof value !== 'object' || !value.scopes ||
                    !value.scopes.launch || !value.scopes.manual) { throw new Error('Invalid snapshot'); }
            if (state.dialog && state.payload && state.payload.account_key !== value.account_key) { showReset(false); }
            state.payload = value;
            state.actionError = null;
            applyAppearance(value.appearance);
            render();
            if (state.bound) { queueResize(); }
            return true;
        } catch (error) {
            setStatus('Nie udało się odczytać danych statystyk.');
            return false;
        }
    }
    function invoke(action, extra) {
        var args = { action: action }, key;
        if (extra) { for (key in extra) { if (Object.prototype.hasOwnProperty.call(extra, key)) { args[key] = String(extra[key]); } } }
        try {
            var model = window.model;
            var command = model && model.onAction;
            if (typeof command === 'function') { command.call(model, args); return true; }
            if (command && typeof command.value === 'function') { command.value.call(command, args); return true; }
            if (typeof window.GRZSessionStats.onAction === 'function') {
                window.GRZSessionStats.onAction(args); return true;
            }
        } catch (error) {
            if (action !== 'resize' && action !== 'diagnostic' && action !== 'viewport') {
                state.actionError = 'Nie udało się wykonać polecenia. Spróbuj ponownie.';
                setStatus(state.actionError);
            }
            return false;
        }
        if (action !== 'resize' && action !== 'diagnostic' && action !== 'viewport') { setStatus('Brak połączenia z grą.'); }
        return false;
    }
    function focusControl(node) {
        /* Focus support differs between Gameface releases. It must never stop a tab change. */
        if (node && typeof node.focus === 'function') {
            try { node.focus(); } catch (error) { /* Mouse interaction remains available. */ }
        }
    }
    function nativeMove(on) {
        if (!state.bound || !window.viewEnv || typeof window.viewEnv.handleViewEvent !== 'function') { return false; }
        try {
            /* The client's sendEvent.move helper (tutorial.js / MembersWindow).
               Wulf moves the native window; the DOM always stays at its own origin. */
            window.viewEnv.handleViewEvent({__Type:'GFViewEventProxy', type:16, isMouseEvent:true, on:on});
            return true;
        } catch (error) { return false; }
    }
    function endNativeDrag() {
        if (!state.dragging) { return; }
        state.dragging = false;
        nativeMove(false);
        invoke('drag', {active:false});
    }
    function beginNativeDrag(event) {
        if (!event || event.button !== 0 || state.dialog || state.dragging) { return; }
        var target = event.target;
        while (target && target !== nodes.titlebar) {
            if (target === nodes.close || target.tagName === 'BUTTON') { return; }
            target = target.parentNode;
        }
        if (target !== nodes.titlebar) { return; }
        if (nativeMove(true)) {
            state.dragging = true;
            /* Only a placement hint: this command does not implement dragging. */
            invoke('drag', {active:true});
            event.preventDefault();
        }
    }
    function showReset(show) {
        if (show) { endNativeDrag(); }
        state.dialog = !!show;
        document.getElementById('ss-confirm-title').textContent = state.scope === 'instance' ?
            'Wyzerować zakres „Cała instancja”?' : 'Wyzerować zakres „Od resetu”?';
        document.getElementById('ss-confirm-message').textContent = state.scope === 'instance' ?
            'Nowy wspólny zakres zacznie się teraz. Historie kont i ich ręczne resety pozostaną bez zmian.' :
            'Nowy zakres zacznie się teraz tylko dla bieżącego konta. Pozostałe konta pozostaną bez zmian.';
        nodes['reset-overlay'].style.display = show ? 'flex' : 'none';
        if (show) { focusControl(nodes['reset-cancel']); } else if (state.scope !== 'launch') { focusControl(nodes.reset); }
    }
    function switchScope(scope) {
        if (!state.payload || !state.payload.scopes[scope]) { return; }
        state.scope = scope; state.loadedCount = 40;
        showReset(false); nodes.scroll.scrollTop = 0; render();
    }
    function switchGroup(group) {
        if (state.group !== group) { state.loadedCount = 40; }
        state.group = group; nodes.scroll.scrollTop = 0; render();
    }
    function switchXP(xp) { state.xp = xp; render(); }
    document.getElementById('ss-scope-launch').onclick = function () { switchScope('launch'); };
    document.getElementById('ss-scope-manual').onclick = function () { switchScope('manual'); };
    document.getElementById('ss-scope-instance').onclick = function () { switchScope('instance'); };
    document.getElementById('ss-xp-base').onclick = function () { switchXP('base'); };
    document.getElementById('ss-xp-received').onclick = function () { switchXP('received'); };
    document.getElementById('ss-group-vehicles').onclick = function () { switchGroup('vehicles'); };
    document.getElementById('ss-group-maps').onclick = function () { switchGroup('maps'); };
    document.getElementById('ss-group-battles').onclick = function () { switchGroup('battles'); };
    nodes.close.onclick = function () { if (state.dialog) { showReset(false); } else { invoke('close'); } };
    nodes.refresh.onclick = function () { invoke('refresh'); };
    nodes.reset.onclick = function () { if (state.scope !== 'launch') { showReset(true); } };
    nodes['reset-cancel'].onclick = function () { showReset(false); };
    nodes['reset-confirm'].onclick = function () {
        if (state.scope !== 'launch' && state.dialog && invoke('reset', {
                scope:state.scope, account_key:state.payload.account_key
            })) { showReset(false); }
    };
    nodes.scroll.addEventListener('scroll', loadNearBottom);
    root.addEventListener('wheel', onNativeWheel, false);
    nodes.titlebar.addEventListener('mousedown', beginNativeDrag);
    document.addEventListener('mouseup', endNativeDrag);
    window.addEventListener('blur', endNativeDrag);
    document.addEventListener('keydown', function (event) {
        var key = event.key || event.keyCode;
        if (key === 'Escape' || key === 27) {
            event.preventDefault();
            endNativeDrag();
            if (state.dialog) { showReset(false); } else { invoke('close'); }
        }
        if (state.dialog && (key === 'Tab' || key === 9)) {
            if (event.shiftKey && document.activeElement === nodes['reset-cancel']) {
                event.preventDefault(); focusControl(nodes['reset-confirm']);
            } else if (!event.shiftKey && document.activeElement === nodes['reset-confirm']) {
                event.preventDefault(); focusControl(nodes['reset-cancel']);
            }
        }
    });

    function readModel() {
        if (state.destroyed || !state.bound) { return; }
        // Optional Gameface registration can fail during readiness. Keep the
        // engine listener and initial model usable; retry on the next update.
        if (!state.callbackRegistering && state.callbackId === null && window.viewEnv && typeof window.viewEnv.addDataChangedCallback === 'function') {
            state.callbackRegistering = true;
            try {
                var callbackId = window.viewEnv.addDataChangedCallback('model', 0, true);
                if (callbackId !== undefined && callbackId !== null) { state.callbackId = callbackId; }
            } catch (error) { /* A later model event or readiness pass can retry. */ }
            finally { state.callbackRegistering = false; }
        }
        var model = window.model;
        if (model && model.payload !== undefined) { update(model.payload); }
    }
    function nativeDiagnostic(stage, width, height) {
        if (!state.bound || state.diagnostics[stage]) { return; }
        state.diagnostics[stage] = true;
        invoke('diagnostic', {stage:stage, width:width || 0, height:height || 0, scale:state.nativeScale});
    }
    function resizeNative() {
        if (!state.bound) { return; }
        var rect = root.getBoundingClientRect();
        var width = Math.max(1, Math.ceil(rect.width));
        var height = Math.max(1, Math.ceil(rect.height));
        if (state.nativeWidth === width && state.nativeHeight === height) { return; }
        state.nativeWidth = width;
        state.nativeHeight = height;
        /* Surface sizing is optional here: Python must still receive the dimensions
           and centre the window if a client helper is absent or throws. */
        if (window.viewEnv && typeof window.viewEnv.resizeViewPx === 'function') {
            try { window.viewEnv.resizeViewPx(width, height); } catch (error) { /* Keep the centring measurement available to Python. */ }
        }
        invoke('resize', { width: width, height: height });
        nativeDiagnostic('layout_ready', width, height);
    }
    function queueResize() {
        var viewport = state.payload && state.payload.viewport;
        /* IGuiLoader.scale is supplied by the Python adapter. Never use browser DPR. */
        var scale = viewport && viewport.scale;
        if (!hasNumber(scale) || scale <= 0) {
            scale = 1;
            if (window.viewEnv && typeof window.viewEnv.remToPx === 'function') {
                try {
                    var fallback = window.viewEnv.remToPx(1);
                    if (hasNumber(fallback) && fallback > 0) { scale = fallback; }
                } catch (error) { /* Unsupported helper must not prevent centring. */ }
            }
        }
        state.nativeScale = scale;
        document.documentElement.style.fontSize = scale + 'px';
        if (state.bound && viewport) {
            if (hasNumber(viewport.width) && viewport.width > 0) {
                var availableWidth = Math.max(1, Math.floor(viewport.width - 20));
                root.style.maxWidth = availableWidth + 'px';
                root.style.minWidth = Math.min(300, availableWidth) + 'px';
            }
            if (hasNumber(viewport.height) && viewport.height > 0) {
                root.style.maxHeight = Math.max(1, Math.floor(viewport.height - 20)) + 'px';
            }
        }
        if (typeof window.requestAnimationFrame === 'function') {
            window.requestAnimationFrame(function () { window.requestAnimationFrame(resizeNative); });
        } else { resizeNative(); }
    }
    function onScaleUpdated() {
        if (state.destroyed) { return; }
        /* Fetch the current IGuiLoader scale before trusting the previous snapshot again. */
        invoke('viewport');
        queueResize();
    }
    function bindModel() {
        if (state.destroyed) { return; }
        if (state.bound) { readModel(); queueResize(); return; }
        if (!window.engine || !window.viewEnv) { return; }
        state.bound = true;
        document.documentElement.className += ' ss-native-document';
        root.className += ' is-native';
        nativeDiagnostic('dom_ready');
        window.engine.on('viewEnv.onDataChanged', readModel);
        window.engine.on('self.onScaleUpdated', onScaleUpdated);
        readModel();
        nativeDiagnostic('model_bound');
        queueResize();
    }
    function afterEngineReady() {
        if (window.isDomBuilt) { bindModel(); }
        else { window.engine.on('self.onDomBuilt', bindModel); }
    }
    function cleanup() {
        if (state.destroyed) { return; }
        state.destroyed = true;
        clearAppearance();
        state.scrollSpeed = 1;
        endNativeDrag();
        root.removeEventListener('wheel', onNativeWheel, false);
        nodes.titlebar.removeEventListener('mousedown', beginNativeDrag);
        document.removeEventListener('mouseup', endNativeDrag);
        window.removeEventListener('blur', endNativeDrag);
        // Invalidate local ownership before calling the disappearing bridge.
        var wasBound = state.bound, callbackId = state.callbackId;
        state.callbackId = null;
        state.callbackRegistering = false;
        state.bound = false;
        if (wasBound) {
            try {
                if (window.engine && typeof window.engine.off === 'function') {
                    window.engine.off('viewEnv.onDataChanged', readModel);
                }
            } catch (error) { /* Continue removing the other native listeners. */ }
            try {
                if (window.engine && typeof window.engine.off === 'function') {
                    window.engine.off('self.onScaleUpdated', onScaleUpdated);
                }
            } catch (error) { /* Continue removing the other native listeners. */ }
            try {
                if (window.engine && typeof window.engine.off === 'function') {
                    window.engine.off('self.onDomBuilt', bindModel);
                }
            } catch (error) { /* Model callback removal remains independent. */ }
        }
        try {
            if (callbackId !== null && window.viewEnv && typeof window.viewEnv.removeDataChangedCallback === 'function') {
                window.viewEnv.removeDataChangedCallback(callbackId, 0);
            }
        } catch (error) { /* The destroyed document no longer owns this callback. */ }
    }
    window.GRZSessionStats = {
        update: update,
        onAction: null,
        getState: function () { return { scope:state.scope, group:state.group, xp:state.xp, nativeBound:state.bound, dragging:state.dragging }; },
        destroy: cleanup
    };
    window.addEventListener('beforeunload', cleanup);
    function connectNative() {
        if (state.connecting) { return; }
        if (window.engine && window.engine.whenReady && typeof window.engine.whenReady.then === 'function') {
            state.connecting = true;
            window.engine.whenReady.then(afterEngineReady);
        }
    }
    document.addEventListener('DOMContentLoaded', connectNative);
    window.addEventListener('load', connectNative);
    connectNative();
}());
