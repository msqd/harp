import { expect, test } from '@playwright/test'

for (const scenario of [{name:'desktop-last-row',rows:2,width:1280,height:720},{name:'scrolled-compact',rows:24,width:760,height:480}]) {
  test(scenario.name + ' supports mouse and keyboard actions without clipping', async ({page},info) => {
    await page.setViewportSize({width:scenario.width,height:scenario.height})
    await page.goto('/')
    await page.getByRole('link',{name:'System',exact:true}).waitFor()
    await page.evaluate(rows => {
      const {worker,http,HttpResponse} = (window as any).msw
      const endpoints = Array.from({length:rows},(_,i) => ({settings:{url:`https://remote-${i+1}.example.com/`},status:1}))
      const response = {endpoints:[{settings:{name:'example',port:8080},remote:{current_pool:endpoints.map(e=>e.settings.url),endpoints}}]}
      worker.use(http.get('/api/system/proxy',()=>HttpResponse.json(response)),http.put('/api/system/proxy',async ({request})=>{document.documentElement.dataset.lastMutation=JSON.stringify(await request.json());return HttpResponse.json(response)}))
    },scenario.rows)
    await page.getByRole('link',{name:'System',exact:true}).click()
    const trigger=page.getByRole('button',{name:'up',exact:true}).last()
    await trigger.scrollIntoViewIfNeeded()
    const before=await trigger.boundingBox()
    await trigger.click()
    for (const name of ['Set checking','Set down']) {
      const item=page.getByRole('menuitem',{name})
      await expect(item).toBeVisible();await expect(item).toBeInViewport()
      await expect.poll(()=>item.evaluate(e=>{const r=e.getBoundingClientRect();return e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))})).toBe(true)
    }
    const after=await trigger.boundingBox()
    expect(after!.y).toBeCloseTo(before!.y,0)
    const menu=page.getByRole('menu')
    await info.attach('geometry.json',{body:JSON.stringify({scenario,before,after,menu:await menu.boundingBox(),scroll:await page.evaluate(()=>({window:scrollY,elements:Array.from(document.querySelectorAll('*')).filter(e=>e.scrollTop>0).map(e=>({tag:e.tagName,scrollTop:e.scrollTop}))}))},null,2),contentType:'application/json'})
    await page.screenshot({path:info.outputPath('open-menu.png')})
    const scrollAmount = () => page.evaluate(() => Array.from(document.querySelectorAll('*')).reduce((total,e) => total + e.scrollTop, 0))
    const lockedScroll = await scrollAmount()
    await page.mouse.move(150,250)
    await page.mouse.wheel(0,-60)
    if (scenario.rows > 2) await expect.poll(scrollAmount).toBeLessThan(lockedScroll)
    await expect(trigger).toBeInViewport({ratio:1})
    await page.screenshot({path:info.outputPath('open-menu-after-scroll.png')})
    for (const name of ['Set checking','Set down']) {
      const item=page.getByRole('menuitem',{name})
      await expect(item).toBeInViewport({ratio:1})
      await expect.poll(()=>item.evaluate(e=>{const r=e.getBoundingClientRect();return e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))})).toBe(true)
    }
    await page.getByRole('menuitem',{name:'Set checking'}).click()
    await expect.poll(()=>page.locator('html').getAttribute('data-last-mutation')).toBe(JSON.stringify({endpoint:'example',url:`https://remote-${scenario.rows}.example.com/`,action:'checking'}))
    await expect(menu).not.toBeVisible()
    await trigger.focus();await page.keyboard.press('ArrowDown')
    await expect(menu).toBeVisible()
    await page.keyboard.press('End')
    await expect(page.getByRole('menuitem',{name:'Set down'})).toHaveAttribute('data-focus','')
    await page.keyboard.press('Enter')
    await expect.poll(()=>page.locator('html').getAttribute('data-last-mutation')).toBe(JSON.stringify({endpoint:'example',url:`https://remote-${scenario.rows}.example.com/`,action:'down'}))
    await expect(menu).not.toBeVisible()
    await trigger.focus();await page.keyboard.press('Enter')
    await expect(menu).toBeVisible();await page.keyboard.press('Escape')
    await expect(menu).not.toBeVisible();await expect(trigger).toBeFocused()
    if (scenario.rows > 2) {
      const unlockedScroll = await scrollAmount()
      expect(unlockedScroll).toBeGreaterThan(0)
      await page.mouse.move(150,250)
      await page.mouse.wheel(0,-180)
      await expect.poll(scrollAmount).toBeLessThan(unlockedScroll)
    }
  })
}
