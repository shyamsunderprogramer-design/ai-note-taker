// Debug access is an explicit local development choice, never a packaged default.
function configureRuntimePrivacy({app, inspector, env = process.env}) {
  const localQA = !app.isPackaged && env.ANT_ENABLE_LOCAL_QA === '1'
  if (!localQA) {
    for (const flag of ['remote-debugging-port', 'remote-debugging-pipe', 'inspect', 'inspect-brk']) app.commandLine.removeSwitch(flag)
    inspector?.close()
  } else {
    app.commandLine.appendSwitch('remote-debugging-address', '127.0.0.1')
  }
  return {localQA}
}
module.exports = {configureRuntimePrivacy}
