$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$mod = Join-Path $root 'unity_project\Assets\BlasDeLezoMod'
# Generated assets are rebuilt from scratch: a reused mesh asset can keep stale data.
foreach ($g in 'BlasDeLezoBody.asset', 'BlasDeLezoHeadRigidSkin.asset', 'Skin.prefab', 'Skin_pic.prefab') {
  foreach ($f in (Join-Path $mod $g), (Join-Path $mod "$g.meta")) { if (Test-Path $f) { Remove-Item $f -Force } }
}
Copy-Item (Join-Path $root 'build\marta\Skin.fbx') $mod -Force
foreach ($t in 'BlasDeLezo_BaseColor.png', 'BlasDeLezo_Normal.png', 'BlasDeLezo_ORM.png') { Copy-Item (Join-Path $root "build\$t") $mod -Force }
$unity = 'C:\Program Files\Unity\Hub\Editor\2019.4.0f1\Editor\Unity.exe'
$log = Join-Path $root 'build\unity_build.log'
$p = Start-Process -FilePath $unity -ArgumentList @('-batchmode', '-quit', '-projectPath', "`"$(Join-Path $root 'unity_project')`"", '-executeMethod', 'BlasDeLezoBuild.Build', '-logFile', "`"$log`"") -PassThru
$p.WaitForExit()  # -Wait would also wait for Unity's helper processes
if ($p.ExitCode -ne 0 -or -not (Select-String -Path $log -Pattern 'BLASDELEZO_MARTA_BUILD_OK' -Quiet)) { throw "Unity build failed, see $log" }
$out = Join-Path $root 'mod_blasdelezo'
$rel = Join-Path $root 'release'
$names = 'skin_marta_blasdelezo', 'skin_marta_blasdelezo.manifest', 'pic_marta_blasdelezo', 'pic_marta_blasdelezo.manifest'
foreach ($n in $names) { Copy-Item (Join-Path $out $n) $rel -Force }
$zip = Join-Path $root 'BlasDeLezo_Marta.zip'
if (Test-Path $zip) { Remove-Item $zip }
$files = @($names | % { Join-Path $rel $_ }) + @('LEEME.txt','Install_BlasDeLezo_Marta.ps1','Install_BlasDeLezo_Marta.cmd','Uninstall_BlasDeLezo_Marta.cmd','marta_fpp_patch.json' | % { Join-Path $rel $_ })
Compress-Archive -Path $files -DestinationPath $zip
"BUILD_OK $zip"
