const {test,expect}=require('@playwright/test');
const {randomUUID}=require('node:crypto');

for(const remember of [true,false]) {
  test(`Remember me ${remember?'on':'off'} controls persistence and renews the session`,async({page,context,browser,request})=>{
    await page.goto('/signin.html');
    const api=await page.evaluate(()=>API_BASE);
    const username='remember_'+randomUUID().replaceAll('-','').slice(0,12);
    const password='TestPass123!';
    const registered=await request.post(api+'/auth/register',{form:{username,email:username+'@example.com',password}});
    expect(registered.ok()).toBeTruthy();
    await page.locator('#siUser').fill(username);
    await page.locator('#siPass').fill(password);
    if(remember){await page.getByRole('checkbox',{name:'Remember me'}).focus();await page.keyboard.press('Space')}
    await page.locator('#siPass').press('Enter');
    await expect(page).toHaveURL(/index\.html$/);
    await page.evaluate(()=>{const s=AuthHelper.getSession();AuthHelper.setSession({...s,expires_at:1},s.remember)});
    expect(await page.evaluate(async()=> (await fetch(API_BASE+'/auth/me')).status)).toBe(200);
    const state=await context.storageState();
    const next=await browser.newContext({storageState:state});
    try {
      const reopened=await next.newPage();
      await reopened.goto(new URL('/signin.html',page.url()).href);
      if(remember){
        await expect(reopened).toHaveURL(/index\.html$/);
        const refresh=await reopened.evaluate(()=>AuthHelper.getSession().refresh_token);
        await reopened.evaluate(()=>AuthHelper.logout());
        const revoked=await request.post(api+'/auth/refresh',{form:{refresh_token:refresh}});
        expect(revoked.status()).toBe(401);
      }else{
        await expect(reopened.locator('#siBtn')).toBeVisible();
        expect(await reopened.evaluate(()=>AuthHelper.getToken())).toBeNull();
      }
    }finally{await next.close()}
  });
}

test('failed login does not replace the saved username',async({page})=>{
  await page.goto('/signin.html');
  await page.evaluate(()=>localStorage.setItem('ainotetaker_remember_user','previous_user'));
  await page.reload();
  await page.locator('#siUser').fill('does_not_exist_'+randomUUID().slice(0,8));
  await page.locator('#siPass').fill('incorrect-password');
  await page.locator('#siRemember').check();
  await page.locator('#siPass').press('Enter');
  await expect(page.locator('#siError')).toBeVisible();
  expect(await page.evaluate(()=>localStorage.getItem('ainotetaker_remember_user'))).toBe('previous_user');
});
