# Step 1: combine the textured GLB (base_basic_pbr.glb: colour, normal and
# metallic-roughness maps) with the skin weights and joints of the rigged GLB
# (base.glb). Both files hold the same generated mesh.
#   blender -b -P step1_prepare.py -- <rigged.glb> <textured.glb> <build_dir>
import bpy, bmesh, os, sys, json
import numpy as np
from mathutils.kdtree import KDTree

RIG, COLOR, OUT = sys.argv[sys.argv.index('--') + 1:][:3]
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)

bpy.ops.import_scene.gltf(filepath=RIG)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
rigged = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices)); rigged.name = 'Rigged'
joints = {b.name: {'head': list(arm.matrix_world @ b.head_local), 'tail': list(arm.matrix_world @ b.tail_local),
                   'parent': b.parent.name if b.parent else None} for b in arm.data.bones}
json.dump(joints, open(os.path.join(OUT, 'source_joints.json'), 'w'), indent=1)
RW = np.array([tuple(rigged.matrix_world @ v.co) for v in rigged.data.vertices])
rnames = [g.name for g in rigged.vertex_groups]
rweights = [{rnames[g.group]: g.weight for g in v.groups} for v in rigged.data.vertices]

before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=COLOR)
mesh = max((o for o in set(bpy.data.objects) - before if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
mesh.parent = None
mesh.data.transform(mesh.matrix_world); mesh.matrix_world.identity()
mesh.name = 'BlasDeLezoBody'
for o in list(bpy.data.objects):
    if o != mesh: bpy.data.objects.remove(o)

# Weight transfer: identical vertices, matched by position.
kd = KDTree(len(RW))
for i, p in enumerate(RW): kd.insert(p, i)
kd.balance()
dmax = 0.
for v in mesh.data.vertices:
    _, j, dist = kd.find(v.co); dmax = max(dmax, dist)
    for n, w in rweights[j].items():
        (mesh.vertex_groups.get(n) or mesh.vertex_groups.new(name=n)).add([v.index], w, 'REPLACE')
print('WEIGHT_TRANSFER max distance', round(dmax, 6), flush=True)

# Export the source textures for Unity.
names = {'texture_diffuse': 'BlasDeLezo_BaseColor.png', 'texture_normal': 'BlasDeLezo_Normal.png',
         'texture_metallic-texture_roughness': 'BlasDeLezo_MR.png'}
for im in bpy.data.images:
    if im.name in names:
        im.filepath_raw = os.path.join(OUT, names[im.name]); im.file_format = 'PNG'; im.save()
# glTF metallic-roughness map (R=1, G=roughness, B=metallic) is the ORM layout the shader reads.
mr = os.path.join(OUT, 'BlasDeLezo_MR.png')
if os.path.exists(mr): os.replace(mr, os.path.join(OUT, 'BlasDeLezo_ORM.png'))

bpy.context.view_layer.objects.active = mesh; mesh.select_set(True)
bm = bmesh.new(); bm.from_mesh(mesh.data)
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)
bm.to_mesh(mesh.data); bm.free()
# One Catmull-Clark level for a smoother silhouette; UVs and weights are interpolated.
sub = mesh.modifiers.new('Sub', 'SUBSURF'); sub.levels = 1; sub.render_levels = 1
sub.uv_smooth = 'PRESERVE_BOUNDARIES'
bpy.ops.object.modifier_apply(modifier=sub.name)
for p in mesh.data.polygons: p.use_smooth = True
print('PREP_OK verts', len(mesh.data.vertices), 'groups', len(mesh.vertex_groups), flush=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'prepared.blend'))
