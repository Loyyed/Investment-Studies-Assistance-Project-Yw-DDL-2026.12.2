/* Browser checks for the online publication and extracted offline bundle. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs/promises');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const assert = require('node:assert/strict');
const [url, offlineDir, screenshotDir, executablePath] = process.argv.slice(2);
const widths = [1440, 390, 320];
const codes = ['002507', '600298', '688188', '09992', 'US'];
const fail = (reason) => { throw new Error(reason); };

(async () => {
    assert(url && offlineDir);
    const browser = await chromium.launch({ headless: true, executablePath: executablePath || undefined });
    const receipt = { browser: browser.version(), companies: {}, fileEdits: {}, widths, pageErrors: [] };
    if (screenshotDir) await fs.mkdir(screenshotDir, { recursive: true });
    const shot = async (page, name) => {
        if (screenshotDir) await page.screenshot({ path: path.join(screenshotDir, name + '.png') });
    };
    const checkWidth = async (page, limit) => {
        const width = await page.evaluate(() => document.documentElement.scrollWidth);
        assert(width <= limit, String(width) + ' > ' + limit + ' ' + page.url());
    };
    const download = async (page, locator, expected) => {
        const [result] = await Promise.all([page.waitForEvent('download'), locator.click()]);
        assert.equal(result.suggestedFilename(), expected);
        const actual = await result.path();
        assert((await fs.stat(actual)).size > 100);
        return actual;
    };
    try {
        for (const width of widths) {
            const context = await browser.newContext({ viewport: { width, height: 920 }, acceptDownloads: true,
                                                       reducedMotion: width === 320 ? 'reduce' : 'no-preference' });
            const page = await context.newPage();
            page.on('pageerror', e => receipt.pageErrors.push(String(e)));
            const go = async (target) => {
                const response = await page.goto(target);
                assert.equal(response.status(), 200, target);
            };
            await go(url + '/long-atlas/');
            await checkWidth(page, width);
            assert.equal(await page.locator('.cover-card').count(), 5);
            await shot(page, 'cover-' + width);
            if (width === 320) {
                assert.equal(await page.locator('.cover-card').first().evaluate(x => getComputedStyle(x).transitionDuration), '0s');
            }
            for (const code of codes) {
                await page.locator('.cover-card[href="' + code + '/index.html"]').click();
                await checkWidth(page, width);
                assert(page.url().includes('/'+code+'/'));
                const document = await page.locator('#company-document').textContent().then(JSON.parse);
                const visible = await page.locator('[data-prose]').evaluateAll(elements =>
                    Object.fromEntries(elements.map(e => [e.id, e.textContent])));
                assert.deepEqual(visible, document.paragraphs, code + ' chapter prose');
                assert(document.han >= 20000);
                assert.equal(await page.locator('[data-data-figure]').count(), document.figures.length);
                assert.equal(await page.locator('[data-mechanism]').count(), document.mechanisms.length);
                if (width <= 390) await page.locator('.rail summary').click();
                await page.locator('.rail a[href="#chapter-4"]').click();
                assert(page.url().endsWith('#chapter-4'));
                if (width <= 390) assert.equal(await page.locator('.rail details').getAttribute('open'), null);
                assert(await page.locator('#chapter-4').isVisible());
                const figure = page.locator('#chapter-4 [data-data-figure]').first();
                await figure.locator('button[data-mode="table"]').click();
                assert(await figure.locator('[data-view="table"]').isVisible());
                await figure.locator('summary').click();
                assert(await figure.getByRole('link', { name: '同源底表或模型' }).isVisible());
                await checkWidth(page, width);
                if (width === 390 && code === '002507') await shot(page, 'chart-table-390');
                if (width === 1440 && code === '688188') {
                    await page.locator('h1').scrollIntoViewIfNeeded();
                    await shot(page, 'company-1440');
                }
                if (width === 320 && code === '09992') {
                    await page.locator('h1').scrollIntoViewIfNeeded();
                    await shot(page, 'company-320');
                }
                await page.getByRole('link', { name: '图册总封面' }).click();
                assert.equal(await page.locator('.cover-card').count(), 5);
                receipt.companies[code] ||= { visual: [], han: document.han, figures: document.figures.length, mechanisms: document.mechanisms.length };
                receipt.companies[code].visual.push(width);
            }
            if (width === 1440) {
                await go(url + '/desk/');
                await page.getByRole('link', { name: '打开五家公司长篇图册' }).click();
                await page.getByRole('link',{name:'五家同日比较'}).click();
                assert.equal(await page.locator('tbody tr').count(), 5);
                await go(url + '/long-atlas/US/#chapter-6');
                await page.selectOption('#company-picker','../002507/index.html');
                await page.waitForURL('**/002507/index.html');
                const evidence = await page.getByRole('link',{name:'当前 Fact 与来源绑定'}).getAttribute('href');
                await go(url+evidence);
                await go(url + '/long-atlas/09992/');
                await page.locator('#edit-toggle').click();
                const editable = page.locator('[data-prose]').first();
                const probe = (await editable.textContent()) + ' 本地草稿验收';
                await editable.fill(probe);
                await page.locator('#save-draft').click();
                assert((await page.locator('#revision').textContent()).includes('已保存在'));
                await page.reload();
                assert.equal(await editable.textContent(), probe);
                const exported = await download(page, page.locator('#export-draft'), '09992-atlas-draft.json');
                const saved = JSON.parse(await fs.readFile(exported,'utf-8'));
                assert(Object.values(saved.draft.paragraphs).includes(probe));
                const mdFile = await download(page,page.getByRole('link',{name:'在线正文 MD'}),'case.md');
                assert((await fs.readFile(mdFile,'utf-8')).includes('# 泡泡玛特'));
                await download(page,page.getByRole('link',{name:'可编辑 JSON'}),'document.json');
                await go(url+'/long-atlas/');
                await download(page,page.getByRole('link',{name:'完整离线包 ZIP'}),'offline.zip');
                receipt.edit = { reload: true, export: true, md: true, publishedJson: true, offlineZip: true };
                await go(url+'/long-atlas/002507/');
                await page.keyboard.press('Tab');
                assert.equal(await page.evaluate(() => document.activeElement.className), 'skip');
                await page.keyboard.press('Enter');
                assert(page.url().endsWith('#main'));
                receipt.keyboard=true;
            }
            await context.close();
        }
        const context = await browser.newContext({ offline: true, viewport: { width: 390, height: 850 } });
        const page = await context.newPage();
        const offline = pathToFileURL(path.join(offlineDir,'index.html')).href;
        await page.goto(offline);
        for (const code of codes) {
            await page.locator('.cover-card[href="' + code + '/index.html"]').click();
            const document = await page.locator('#company-document').textContent().then(JSON.parse);
            assert.equal(await page.locator('[data-prose]').count(),Object.keys(document.paragraphs).length);
            assert.equal(await page.locator('[data-data-figure]').count(),document.figures.length);
            await page.locator('[data-data-figure] summary').first().click();
            const source = await page.getByRole('link',{name:'同源底表或模型'}).first().getAttribute('href');
            const resolved = new URL(source,page.url());
            assert.equal(resolved.protocol,'file:');
            assert(await fs.stat(resolved).then(x=>x.size>100));
            await page.locator('button[data-mode="table"]').first().click();
            assert.equal(await page.locator('[data-view="table"]:visible').count(),1);
            await checkWidth(page,390);
            await page.getByRole('link',{name:'图册总封面'}).click();
        }
        receipt.offline = { browserOffline: true, companies: codes, tables: true };
        await context.close();
        if (receipt.pageErrors.length) fail(receipt.pageErrors.join('\n'));
        console.log(JSON.stringify(receipt,null,2));
    } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode=1; });
