# Blas de Lezo: exclusive custom skin for Marta (Hellish Quart)

A fan-made skin that works only for Marta. It runs on Marta's native 68-joint skeleton (Mafra5/Marfa), with her original moves and rapier, and ships with the Marta first-person (FPP) compatibility adjustment.

- **Immobile left arm.** Marta fights with her right arm. The left arm, like Blas de Lezo's arm without mobility, hangs at his side. It is bound to the chest (`Spine1`), so it follows the torso but never Marta's left-arm animation.
- **Wooden left leg**, from the source model.
- **Rigid head and wig.**
- **Same proportions as the source model.** Blas is much taller than Marta, so the whole model is scaled uniformly to Marta's shoulder height (×0.936). Nothing is stretched or squashed.

## Layout

- `model/BlasDeLezo_tpose.glb`: the source model in T-pose. It contains PBR textures (diffuse 4096, normal and metallic-roughness 2048) and its own 52-bone rig with skin weights. `model/references/` holds the four reference views.
- `model/selector_portrait.png`: the painted portrait used as the selector image.
- `blender_work/step1_prepare.py`: reads the mesh, rig joints and weights, applies one subdivision level and exports the textures. The glTF MR map is used directly as the shader's ORM.
- `blender_work/step3_rig_marta.py`: scales the model to Marta's shoulder height and fits Marta's limbs and hands to the source joints. It poses, bakes and binds the immobile left arm, carries the mesh into Marta's bind pose and splits off the rigid head. It exports `Skin.fbx` and QA renders.
- `blender_work/verify_skeleton.py`: checks that `Skin.fbx` holds exactly Marta's 68 bones and that every vertex has valid weights.
- `unity_project/`: Unity 2019.4.0f1 project (menu **BlasDeLezo → Construir mod**). It builds `skin_marta_blasdelezo` and `pic_marta_blasdelezo`.
- `release/`: the installer (`.cmd`/`.ps1`), the FPP patch data and `LEEME.txt`.

## Rebuild

Copy `Hellish Quart_Data/Managed/PlayMaker.dll` from your own installation to `unity_project/Assets/Plugins/`, then run:

```powershell
$blender="C:\Program Files\Blender Foundation\Blender 5.3\blender.exe"
$skel="unity_project\Assets\BlasDeLezoMod\Editor\MartaSkeleton.json"
& $blender -b --factory-startup -P blender_work\step1_prepare.py -- model\BlasDeLezo_tpose.glb model\BlasDeLezo_tpose.glb build
& $blender -b --factory-startup -P blender_work\step3_rig_marta.py -- build $skel
& $blender -b --factory-startup -P blender_work\verify_skeleton.py -- build\marta\Skin.fbx $skel
.\build.ps1
```

`build.ps1` runs the Unity batch build and copies the four bundles into `release/`. It also creates `BlasDeLezo_Marta.zip`.

## FPP adjustment

The installer changes 4 bytes of Marta's skin loader (PlayMaker FSM, path ID 67770) in `resources.assets`. On Steam build 26432078 the true event of `isFPP?` goes from `yes` to `no`, so first person uses the selected custom skin. Before writing anything, it checks the 15,936-byte block by SHA-256. It saves that block to `marta_loader_backup.bin` and verifies the result.
