'use strict';

const metricHolder = '#ss-sort-metric';
const metricTrigger = `${metricHolder} .ss-select-trigger`;
const source = '#ss-summary .ss-metric-battle-link[data-ss-source-metric="xp_received"][data-ss-extreme="max"]';
const battleBack = '.ss-battle-target .ss-battle-return';

function pointInView(selector) {
  const node = document.querySelector(selector);
  if (!node) return null;
  const box = node.getBoundingClientRect();
  const x = (box.left + box.right) / 2, y = (box.top + box.bottom) / 2;
  const hit = document.elementFromPoint(x, y);
  return box.width > 0 && box.height > 0 && hit && node.contains(hit) ? {x, y} : null;
}

async function reveal(ctx, selector, budget = {remaining:3}) {
  for (;;) {
    const point = await ctx.driver.evaluate(pointInView, selector);
    if (point) return point;
    if (!budget.remaining) break;
    const wheel = await ctx.driver.evaluate(() => {
      const scroll = document.getElementById('ss-scroll');
      const box = scroll.getBoundingClientRect();
      const filter = document.getElementById('ss-filter-panel');
      const top = filter.classList.contains('is-pinned') ? Math.max(box.top, filter.getBoundingClientRect().bottom) : box.top;
      for (const x of [box.left + 8, (box.left + box.right) / 2]) {
        const y = (top + box.bottom) / 2;
        if (y > top && scroll.contains(document.elementFromPoint(x, y))) return {x, y};
      }
      return null;
    });
    if (!wheel) break;
    budget.remaining--;
    await ctx.driver.wheel(wheel.x, wheel.y, -120);
    await ctx.idle();
  }
  throw new Error(`${selector} could not be reached within three wheel movements`);
}

async function sortMenu(ctx, task) {
  await ctx.setup({...task, range:'launch', group:'vehicles'});
  const budget = {remaining:3};
  if (await ctx.driver.evaluate(() => document.querySelector('#ss-sort-metric .ss-select-trigger').disabled)) {
    await reveal(ctx, '#ss-sort-off', budget);
    await ctx.click('#ss-sort-off');
  }
  await reveal(ctx, metricTrigger, budget);
  await ctx.click(metricTrigger);
  const endpoint = () => ctx.driver.evaluate(() => {
    const menu = document.getElementById('ss-options-metric');
    const options = Array.prototype.filter.call(menu.querySelectorAll('[role="option"]'), node =>
      !node.disabled && getComputedStyle(node).display !== 'none');
    const option = document.activeElement;
    if (!option || !menu.contains(option)) return null;
    const box = option.getBoundingClientRect(), menuBox = menu.getBoundingClientRect();
    const center = document.elementFromPoint((box.left + box.right) / 2, (box.top + box.bottom) / 2);
    return {position:options.indexOf(option), total:options.length, visible:box.height > 0 &&
      box.top >= menuBox.top - 1 && box.bottom <= menuBox.bottom + 1 && center && option.contains(center)};
  });
  await ctx.driver.press('End');
  await ctx.idle();
  const end = await endpoint();
  await ctx.check(end && end.total > 1 && end.position === end.total - 1 && end.visible,
    'End focuses the last sortable field inside the visible menu');
  await ctx.snapshot('sort-menu-end');
  await ctx.driver.press('Home');
  await ctx.idle();
  const home = await endpoint();
  await ctx.check(home && home.position === 0 && home.visible, 'Home returns to the first visible option');
  await ctx.driver.press('Escape');
  await ctx.check(await ctx.driver.evaluate(selector => document.activeElement === document.querySelector(selector), metricTrigger),
    'Escape returns keyboard focus to the sort control');
}

async function calendar(ctx, task) {
  await ctx.setup({...task, range:'since-sunday', group:'vehicles'});
  const before = await ctx.driver.evaluate(() => JSON.parse(window.model.payload).scopes.timeline.from_date);
  await ctx.select('#ss-timeline-from', '__custom__');
  await ctx.click('#ss-custom-date-calendar-from');
  await ctx.check(await ctx.driver.evaluate(() => {
    const root = document.getElementById('grz-session-stats').getBoundingClientRect();
    const dialog = document.getElementById('ss-date-picker-from');
    if (!dialog) return false;
    const box = dialog.getBoundingClientRect();
    return box.width > 0 && box.height > 0 && box.left >= root.left - 1 && box.right <= root.right + 1 &&
      box.top >= root.top - 1 && box.bottom <= root.bottom + 1 && !!dialog.querySelector('.ss-date-day[aria-selected="true"]');
  }), 'Custom calendar, its grid and confirmation fit inside the panel');
  await ctx.driver.press('ArrowRight');
  await ctx.snapshot('calendar');
  await ctx.click('#ss-custom-date-apply-from');
  await ctx.flush();
  await ctx.idle();
  await ctx.check(await ctx.driver.evaluate(previous => {
    const range = JSON.parse(window.model.payload).scopes.timeline;
    return range.from_point === '__custom__' && range.from_date > previous &&
      !document.getElementById('ss-date-picker-from');
  }, before), 'Applying the calendar commits a different custom range to Python and closes the dialog');
}

async function details(ctx, task, group) {
  await ctx.setup({...task, range:'since-sunday', group});
  const more = '#ss-groups .ss-group .ss-more-button';
  await reveal(ctx, more);
  await ctx.click(more);
  await ctx.idle();
  await ctx.check(await ctx.driver.evaluate(more => {
    const button = document.querySelector(more);
    if (!button || button.getAttribute('aria-expanded') !== 'true') return false;
    const card = document.querySelector('#ss-groups .ss-group');
    const detail = card.querySelector('.ss-map-battles');
    if (!detail || detail.getBoundingClientRect().height <= 0) return false;
    return detail.getAttribute('aria-busy') !== 'true' && !!detail.querySelector('.ss-map-battle-row');
  }, more), 'More expands the battle list ordered by Python');
  await ctx.snapshot(`details-${group}`);
  await ctx.click(more);
  await ctx.check(await ctx.driver.evaluate(selector => document.querySelector(selector).getAttribute('aria-expanded') === 'false', more),
    'Less collapses the details again');
}

function interactionResize(width, height) {
  if (width <= 365 && height <= 730) return null;
  return {width: height > 730 ? width : Math.max(365, width - 120), height: 730, simulatedHostResize:true};
}

async function selectedBattle(ctx, task) {
  await ctx.setup({...task, range:'since-sunday', group:'vehicles'});
  const id = await ctx.driver.evaluate(selector => document.querySelector(selector)?.getAttribute('data-battle-id'), source);
  await ctx.check(Boolean(id), 'The maximum received XP has a battle link');
  await ctx.click(source);
  await ctx.flush();
  await ctx.idle();
  const selected = () => ctx.driver.evaluate(id => {
    const cards = document.querySelectorAll('.ss-battle-target');
    return cards.length === 1 && cards[0].getAttribute('data-group-id') === id &&
      document.getElementById('ss-group-battles').getAttribute('aria-pressed') === 'true';
  }, id);
  const visibleSelection = async () => await selected() && ctx.driver.evaluate(pointInView, battleBack);
  const wait = ctx.until || (async (predicate, message) => ctx.check(await predicate(), message));
  await wait(visibleSelection, 'The link must select the matching battle and reveal the Back control');
  await ctx.snapshot('battle-selected');
  const resized = ctx.resize ? interactionResize(task.width, task.height) : null;
  if (resized) {
    await ctx.resize(resized.width, resized.height);
    await wait(visibleSelection, 'The selected battle must stay visible after a simulated host resize');
    await ctx.snapshot('battle-resized');
  }
  const more = '.ss-battle-target .ss-more-button';
  await ctx.click(more);
  await ctx.idle();
  await ctx.check(await ctx.driver.evaluate(() => {
    const detail = document.querySelector('.ss-battle-target .ss-more-panel');
    if (!detail || detail.getBoundingClientRect().height <= 0) return false;
    const titles = Array.from(detail.querySelectorAll('.ss-more-mission-name strong'), node => node.textContent.trim());
    return titles.length >= 3 && titles.every(title => title && !title.startsWith('local:'));
  }), 'Selected battle details show the fixture missions without leaking a raw identifier');
  await reveal(ctx, '.ss-battle-target .ss-more-mission-block .ss-more-title');
  await ctx.snapshot('details-battles');
  await ctx.click(more);
  await ctx.idle();
  await ctx.click(battleBack);
  await ctx.flush();
  await ctx.idle();
  await wait(() => ctx.driver.evaluate(selector => document.activeElement === document.querySelector(selector) &&
    document.getElementById('ss-group-vehicles').getAttribute('aria-pressed') === 'true' &&
    !document.querySelector('.ss-battle-target'), source), 'Back restores the exact source and removes the selected battle marker');
  await ctx.snapshot('battle-returned');
  return resized;
}

async function runInteractions(ctx, task) {
  await sortMenu(ctx, task);
  await calendar(ctx, task);
  for (const group of ['vehicles', 'maps']) await details(ctx, task, group);
  const resize = await selectedBattle(ctx, task);
  return {cases:['sort-menu', 'custom-calendar', 'vehicle-details', 'map-details', 'battle-details', 'selected-battle-and-back'], resize};
}

module.exports = {interactionResize, runInteractions};
