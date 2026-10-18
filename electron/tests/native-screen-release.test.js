const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const {getBinary}=require('../lib/native-screen-capture');
const build=require('../scripts/build-screen-capture.cjs').default;
test('packaged capture resolves its bundled executable and never compiles at runtime',async t=>{
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'ant-capture-test-'));
  t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
  const binary=path.join(directory,'ant-screen-capture');
  fs.writeFileSync(binary,'fixture',{mode:0o755});
  assert.equal(await getBinary({isPackaged:true,resourcesPath:directory}),binary);
  fs.unlinkSync(binary);
  await assert.rejects(getBinary({isPackaged:true,resourcesPath:directory}),{code:'ENOENT'});
});
test('packaging compiles the selected macOS architecture before copying resources',t=>{
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'ant-build-capture-'));
  t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
  for(const [arch,target] of [[1,'x86_64'],[3,'arm64']]) {
    const calls=[];
    build({electronPlatformName:'darwin',arch,packager:{projectDir:directory}},(...args)=>calls.push(args));
    assert.equal(calls.length,1);assert.ok(calls[0][1].includes(`${target}-apple-macos14.0`));
    assert.ok(calls[0][1].at(-1).endsWith('ant-screen-capture'));
  }
  build({electronPlatformName:'linux'},()=>assert.fail('Non-Mac builds must not compile Swift'));
});
