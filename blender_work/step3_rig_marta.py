# Step 3: bind the textured mesh to Marta's native 68-joint skeleton.
#
# Marta's bones are moved/turned onto the joints of the source rig, the mesh is
# skinned with the source weights (renamed to Marta's bones), and then the
# skeleton is returned to Marta's native rest pose, carrying the mesh into
# Marta's bind space. Head and hat are split into a rigid Head-only part.
import bpy, os, sys, json, math
import numpy as np
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index('--') + 1:]
BUILD, SKELETON = args[0], args[1]
OUT = os.path.join(BUILD, 'marta'); os.makedirs(OUT, exist_ok=True)
# Hanging pose of the immobile left arm (Blender axes: +X left, -Y front, +Z up).
LEFT_ARM_DIR = (0.30, -0.06, -0.95)
LEFT_FOREARM_DIR = (0.08, -0.55, -0.83)
LEFT_HAND_DIR = (0.02, -0.50, -0.87)
bpy.ops.wm.open_mainfile(filepath=os.path.join(BUILD, 'prepared.blend'))
mesh = bpy.data.objects['BlasDeLezoBody']
J = {k: {'head': Vector(v['head']), 'tail': Vector(v['tail'])} for k, v in
     json.load(open(os.path.join(BUILD, 'source_joints.json'))).items()}

# --- Marta skeleton (same conversion as the Alatriste build) -----------------
native = json.load(open(SKELETON))
C = Matrix(((-1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
ad = bpy.data.armatures.new('MartaSkeleton'); arm = bpy.data.objects.new('Armature', ad)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm; arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for n in native['bones']:
    b = ad.edit_bones.new(n['name']); b.length = .05
    W = Matrix(n['world']); R = C @ W.to_3x3().to_4x4() @ C.inverted(); R.translation = C.to_3x3() @ W.translation
    b.matrix = R
    if n['parent']: b.parent = ad.edit_bones[n['parent']]
bpy.ops.object.mode_set(mode='OBJECT')
original = {b.name: b.matrix_local.copy() for b in ad.bones}
origlen = {b.name: b.length for b in ad.bones}

# Blas is much taller than Marta (shoulders 1.53 m vs 1.44 m). Scaling the
# whole model to Marta's shoulder height keeps every proportion; lifting only
# the upper body by ~10 cm would squash the torso instead.
src_shoulder = (J['LeftArm']['head'].z + J['RightArm']['head'].z) / 2
marta_shoulder = (original['LeftArm'].translation.z + original['RightArm'].translation.z) / 2
SCALE = marta_shoulder / src_shoulder
mesh.data.transform(Matrix.Scale(SCALE, 4))
for k in J: J[k] = {'head': J[k]['head'] * SCALE, 'tail': J[k]['tail'] * SCALE}
print('MODEL_SCALE', round(SCALE, 4), flush=True)

# --- Fit Marta's joints to the source rig ------------------------------------
bpy.ops.object.mode_set(mode='EDIT')
eb = ad.edit_bones
def H(n): return eb[n].head.copy()
def apply(n, M):
    for q in [eb[n]] + list(eb[n].children_recursive): q.matrix = M @ q.matrix
def move(n, target): apply(n, Matrix.Translation(Vector(target) - H(n)))
def turn(n, child, target):
    h = H(n); r = (H(child) - h).normalized().rotation_difference((Vector(target) - h).normalized())
    apply(n, Matrix.Translation(h) @ r.to_matrix().to_4x4() @ Matrix.Translation(-h))
def frame(d, l):
    d = d.normalized(); l = (l - d * l.dot(d)).normalized(); return Matrix((d, l, d.cross(l))).transposed()
def align_frame(n, d1, l1, d2, l2):
    h = H(n); R = frame(d2, l2) @ frame(d1, l1).transposed()
    apply(n, Matrix.Translation(h) @ R.to_4x4() @ Matrix.Translation(-h))

# The trunk keeps Marta's joint layout, but the whole upper block (chest,
# shoulders, neck, head) is lifted to the model's shoulder height. Marta's head
# sits ~5 cm higher above her shoulders than these models; fitting only the
# shoulders pulled them down and stretched the neck. The height difference is
# shared between the Hips-Spine and Spine-Spine1 spans of the torso instead.
lift = ((J['LeftArm']['head'].z + J['RightArm']['head'].z) / 2 -
        (H('LeftArm').z + H('RightArm').z) / 2)
move('Spine', H('Spine') + Vector((0, 0, lift / 2)))
move('Spine1', H('Spine1') + Vector((0, 0, lift / 2)))
print('UPPER_BODY_LIFT', round(lift, 4), flush=True)
for s in ('Left', 'Right'):
    move(s + 'Shoulder', J[s + 'Shoulder']['head']); turn(s + 'Shoulder', s + 'Arm', J[s + 'Arm']['head'])
    move(s + 'Arm', J[s + 'Arm']['head']); turn(s + 'Arm', s + 'ForeArm', J[s + 'ForeArm']['head'])
    move(s + 'ForeArm', J[s + 'ForeArm']['head']); turn(s + 'ForeArm', s + 'Hand', J[s + 'Hand']['head'])
    move(s + 'Hand', J[s + 'Hand']['head'])
    hn = s + 'Hand'
    align_frame(hn, H(hn + 'Middle1') - H(hn), H(hn + 'Index1') - H(hn + 'Pinky1'),
                J[hn + 'Middle1']['head'] - J[hn]['head'], J[hn + 'Index1']['head'] - J[hn + 'Pinky1']['head'])
    for f in ('Thumb', 'Index', 'Middle', 'Ring', 'Pinky'):
        for k in (1, 2, 3):
            n = f'{hn}{f}{k}'; tgt = J[f'{hn}{f}{k+1}']['head'] if k < 3 else J[n]['tail']
            move(n, J[n]['head']); turn(n, f'{hn}{f}{k+1}', tgt)
    move(s + 'UpLeg', J[s + 'UpLeg']['head']); turn(s + 'UpLeg', s + 'Leg', J[s + 'Leg']['head'])
    move(s + 'Leg', J[s + 'Leg']['head']); turn(s + 'Leg', s + 'Foot', J[s + 'Foot']['head'])
    move(s + 'Foot', J[s + 'Foot']['head']); turn(s + 'Foot', s + 'ToeBase', J[s + 'ToeBase']['head'])
    move(s + 'ToeBase', J[s + 'ToeBase']['head']); turn(s + 'ToeBase', s + 'ToeBase_END', J[s + 'ToeBase']['tail'])
fit_head = {b.name: b.head.copy() for b in ad.edit_bones}
bpy.ops.object.mode_set(mode='OBJECT')

# --- Weights: source names -> Marta names ------------------------------------
RENAME = {'Spine1': 'Spine', 'Spine2': 'Spine1'}
bone_names = {b.name for b in ad.bones}
names = [g.name for g in mesh.vertex_groups]
per_vertex = []
for v in mesh.data.vertices:
    w = {}
    for g in v.groups:
        n = RENAME.get(names[g.group], names[g.group])
        if n not in bone_names: raise RuntimeError('Unmapped bone ' + n)
        w[n] = w.get(n, 0) + g.weight
    per_vertex.append(w)
V0 = np.array([tuple(v.co) for v in mesh.data.vertices])

# Rigid head: faces fully owned by the head (face, hair, hat).
head_faces = set()
for p in mesh.data.polygons:
    if p.center.z > 1.45 and all(per_vertex[i].get('Head', 0) >= .5 for i in p.vertices):
        head_faces.add(p.index)
head_verts = {i for f in head_faces for i in mesh.data.polygons[f].vertices}
body_verts = {i for p in mesh.data.polygons if p.index not in head_faces for i in p.vertices}
seam = head_verts & body_verts
for i in head_verts: per_vertex[i] = {'Head': 1.}

# Hanging hair below the rigid head: the head's share fades smoothly along the
# locks. It is 1 at the head seam and falls off over HAIR_FADE (geodesic
# distance), and it is 0 where the hair touches the coat or armour, rising over
# CONTACT_FADE. The hair stays attached to the back, the shoulders keep their
# own weights, and a head turn is spread along the locks instead of folding
# them at one line.
import heapq
HAIR_FADE, CONTACT_FADE = .30, .08
nbr = [[] for _ in mesh.data.vertices]
for e in mesh.data.edges:
    a, b = e.vertices; d = (mesh.data.vertices[a].co - mesh.data.vertices[b].co).length
    nbr[a].append((b, d)); nbr[b].append((a, d))
def is_hair(j): return per_vertex[j].get('Head', 0) + per_vertex[j].get('Neck', 0) > .05
def geodesic(src, limit):
    dist = {i: 0. for i in src}; heap = [(0., i) for i in src]
    while heap:
        d, i = heapq.heappop(heap)
        if d > dist.get(i, 1e9): continue
        for j, dd in nbr[i]:
            if j in head_verts or not is_hair(j): continue
            nd = d + dd
            if nd < dist.get(j, 1e9) and nd <= limit:
                dist[j] = nd; heapq.heappush(heap, (nd, j))
    return dist
d_seam = geodesic(seam, HAIR_FADE)
band = [i for i in d_seam if i not in head_verts]
bset = set(band)
contact = [i for i in band if any(j not in head_verts and not is_hair(j) for j, _ in nbr[i])]
d_coat = geodesic(contact, CONTACT_FADE)
def smooth(x): x = min(1., max(0., x)); return x * x * (3 - 2 * x)
for i in band:
    s = (1 - smooth(d_seam[i] / HAIR_FADE)) * smooth(d_coat.get(i, CONTACT_FADE) / CONTACT_FADE)
    w = {n: v * (1 - s) for n, v in per_vertex[i].items()}; w['Head'] = w.get('Head', 0) + s
    per_vertex[i] = w
print('HAIR_FADE head_faces', len(head_faces), 'band_vertices', len(band), 'coat_contact', len(contact), flush=True)

while mesh.vertex_groups: mesh.vertex_groups.remove(mesh.vertex_groups[0])
groups = {}
for i, w in enumerate(per_vertex):
    top = sorted(((n, x) for n, x in w.items() if x > 1e-4), key=lambda t: -t[1])[:4]
    tot = sum(x for _, x in top)
    if tot <= 0: top, tot = [('Hips', 1.)], 1.
    for n, x in top:
        g = groups.get(n) or mesh.vertex_groups.new(name=n); groups[n] = g
        g.add([i], x / tot, 'REPLACE')

# --- Immobile left arm (Blas de Lezo) ----------------------------------------
# Marta fights with her right arm. The left arm is posed hanging at the side,
# baked into the mesh, and bound to the chest (Spine1) so it only follows the
# torso, whatever Marta's animations do with her left arm.
def aim(n, child, d):
    bpy.context.view_layer.update(); pb = arm.pose.bones[n]; m = pb.matrix.copy(); h = m.translation.copy()
    v = arm.pose.bones[child].matrix.translation - h
    r = v.normalized().rotation_difference(Vector(d).normalized()).to_matrix().to_4x4()
    pb.matrix = Matrix.Translation(h) @ r @ Matrix.Translation(-h) @ m; bpy.context.view_layer.update()
mesh.parent = arm
mod = mesh.modifiers.new('LeftArmPose', 'ARMATURE'); mod.object = arm
aim('LeftArm', 'LeftForeArm', LEFT_ARM_DIR)
aim('LeftForeArm', 'LeftHand', LEFT_FOREARM_DIR)
aim('LeftHand', 'LeftHandMiddle1', LEFT_HAND_DIR)
dg = bpy.context.evaluated_depsgraph_get(); eo = mesh.evaluated_get(dg); em = eo.to_mesh()
coords = [v.co.copy() for v in em.vertices]; eo.to_mesh_clear(); mesh.modifiers.remove(mod)
for v, c in zip(mesh.data.vertices, coords): v.co = c
for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
LEFT_ARM = {n for n in bone_names if n == 'LeftShoulder' or n.startswith(('LeftArm', 'LeftForeArm', 'LeftHand'))}
gnames = [g.name for g in mesh.vertex_groups]
moved = 0
for v in mesh.data.vertices:
    w = {gnames[g.group]: g.weight for g in v.groups}
    s = sum(x for n, x in w.items() if n in LEFT_ARM)
    if s <= 0: continue
    moved += 1
    w = {n: x for n, x in w.items() if n not in LEFT_ARM}; w['Spine1'] = w.get('Spine1', 0) + s
    for g in list(v.groups): mesh.vertex_groups[g.group].remove([v.index])
    for n, x in w.items():
        g = mesh.vertex_groups.get(n) or mesh.vertex_groups.new(name=n); g.add([v.index], x, 'REPLACE')
print('LEFT_ARM_IMMOBILE vertices bound to Spine1:', moved, flush=True)

# --- Carry the mesh into Marta's native bind pose ----------------------------
# Limb segments are stretched along their bones while carrying the mesh into
# the target skeleton. The source arms are much shorter than the fighter's bones
# (upper arm ~0.19 vs 0.27 m, forearm ~0.19 vs 0.30 m) and the legs differ too.
# Moving each bone to its target joint without stretching left the whole length
# difference in the blend zones (elbow, wrist, shoulder), which pinched and
# twisted the shoulders and arms in game. Each clavicle, upper arm, forearm, thigh and shin is
# scaled along its own axis from its joint, so every joint lands on the target
# skeleton and the segment between keeps its shape. Linear blend done by hand:
# a stretch along an arbitrary axis is not representable as a pose bone matrix.
mesh.parent = arm
SEGMENTS = [(s + a, s + b) for s in ('Left', 'Right') for a, b in
            (('Shoulder', 'Arm'), ('Arm', 'ForeArm'), ('ForeArm', 'Hand'), ('UpLeg', 'Leg'), ('Leg', 'Foot'))]
stretch = {}
for a, c in SEGMENTS:
    nh = original[a].translation; d = original[c].translation - nh
    r = d.length / max(1e-6, (fit_head[c] - fit_head[a]).length); dn = d.normalized()
    Sm = Matrix.Identity(3) + (r - 1) * Matrix(((dn.x * dn.x, dn.x * dn.y, dn.x * dn.z), (dn.y * dn.x, dn.y * dn.y, dn.y * dn.z), (dn.z * dn.x, dn.z * dn.y, dn.z * dn.z)))
    stretch[a] = Matrix.Translation(nh) @ Sm.to_4x4() @ Matrix.Translation(-nh)
    print('SEGMENT_STRETCH', a, round(r, 3), flush=True)
# The game snaps every skin bone onto the fighter's bone (SetParent with local
# position and rotation reset), so the fighter's joint positions rule. When the
# model's hips sit higher or lower than the fighter's, the hip area had to
# stretch or squash between pelvis and thighs and the arms lost proportion. The lower trunk (Hips and Spine weights) is
# therefore stretched vertically below the chest joint (Spine1), so the mesh hip
# joint lands on the fighter's; the thighs then start right there.
z0 = original['Spine1'].translation.z
mesh_hip = (fit_head['LeftUpLeg'].z + fit_head['RightUpLeg'].z) / 2
native_hip = (original['LeftUpLeg'].translation.z + original['RightUpLeg'].translation.z) / 2
r_trunk = (z0 - native_hip) / max(1e-6, z0 - mesh_hip)
St = Matrix.Translation((0, 0, z0)) @ Matrix.Diagonal((1., 1., r_trunk, 1.)) @ Matrix.Translation((0, 0, -z0))
for n in ('Hips', 'Spine'): stretch[n] = St
print('TRUNK_STRETCH', round(r_trunk, 3), 'mesh_hip', round(mesh_hip, 3), 'native_hip', round(native_hip, 3), flush=True)
Mb = {}
for b in ad.bones:
    M = original[b.name] @ b.matrix_local.inverted()
    Mb[b.name] = stretch[b.name] @ M if b.name in stretch else M
gname = {g.index: g.name for g in mesh.vertex_groups}
coords = []
for v in mesh.data.vertices:
    acc = Vector((0., 0., 0.)); tw = 0.
    for g in v.groups:
        acc += g.weight * (Mb[gname[g.group]] @ v.co); tw += g.weight
    coords.append(acc / tw if tw > 0 else v.co.copy())
for v, c in zip(mesh.data.vertices, coords): v.co = c
bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='EDIT')
for b in ad.edit_bones: b.matrix = original[b.name]; b.length = origlen[b.name]
bpy.ops.object.mode_set(mode='OBJECT')
for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
mod = mesh.modifiers.new('Armature', 'ARMATURE'); mod.object = arm

# --- Materials, split body/head ----------------------------------------------
img = bpy.data.images.load(os.path.join(BUILD, 'BlasDeLezo_BaseColor.png'))
def material(name):
    mt = bpy.data.materials.new(name); mt.use_nodes = True
    tx = mt.node_tree.nodes.new('ShaderNodeTexImage'); tx.image = img
    bs = mt.node_tree.nodes['Principled BSDF']; bs.inputs['Roughness'].default_value = .85
    mt.node_tree.links.new(tx.outputs['Color'], bs.inputs['Base Color']); return mt
mesh.data.materials.clear()
mesh.data.materials.append(material('BlasDeLezoMaterial')); mesh.data.materials.append(material('HeadMaterial'))
for p in mesh.data.polygons: p.material_index = 1 if p.index in head_faces else 0
bpy.ops.object.select_all(action='DESELECT'); mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.separate(type='MATERIAL'); bpy.ops.object.mode_set(mode='OBJECT')
parts = [o for o in bpy.data.objects if o.type == 'MESH']
for o in parts:
    used = {o.data.materials[p.material_index].name for p in o.data.polygons}
    o.name = 'BlasDeLezoHead' if any(n.startswith('HeadMaterial') for n in used) else 'BlasDeLezoBody'
    o.data.name = o.name

# --- QA renders ---------------------------------------------------------------
sc = bpy.context.scene; sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
sc.render.resolution_x = 1000; sc.render.resolution_y = 1200
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.3
def render(n, pos, tgt=(0, 0, 1)):
    cam.location = pos; cam.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(OUT, n + '.png'); bpy.ops.render.render(write_still=True)
render('rest_front', (0, -4, 1)); render('rest_back', (0, 4, 1)); render('rest_side', (4, 0, 1))
def point(n, child, d):
    bpy.context.view_layer.update(); pb = arm.pose.bones[n]; m = pb.matrix; h = m.translation
    v = arm.pose.bones[child].matrix.translation - h
    r = v.normalized().rotation_difference(Vector(d).normalized()).to_matrix().to_4x4()
    pb.matrix = Matrix.Translation(h) @ r @ Matrix.Translation(-h) @ m; bpy.context.view_layer.update()
for s, sg in (('Left', 1), ('Right', -1)):
    point(s + 'Arm', s + 'ForeArm', (sg * .7, 0, .7)); point(s + 'ForeArm', s + 'Hand', (sg * .5, -.3, .7))
render('test_arms_up', (0, -4, 1))
for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
point('RightArm', 'RightForeArm', (-.25, -.7, -.25)); point('RightForeArm', 'RightHand', (.15, -.8, .15))
point('LeftArm', 'LeftForeArm', (.4, .2, -.4))
render('test_guard', (2, -4, 1.1))
for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
cam.data.ortho_scale = .55; render('head_closeup', (0, -4, 1.62), (0, 0, 1.62)); render('head_side', (4, 0, 1.62), (0, 0, 1.62))

# --- Save and export ------------------------------------------------------------
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'BlasDeLezo_Marta.blend'))
bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True)
for o in parts: o.select_set(True)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, 'Skin.fbx'), use_selection=True, object_types={'ARMATURE', 'MESH'},
                         add_leaf_bones=False, bake_anim=False, path_mode='COPY', embed_textures=False,
                         use_mesh_modifiers=False, apply_scale_options='FBX_SCALE_NONE')
report = {'parts': {o.name: {'verts': len(o.data.vertices), 'tris': sum(len(p.vertices) - 2 for p in o.data.polygons)} for o in parts},
          'seam_vertices': len(seam), 'bones': len(ad.bones)}
json.dump(report, open(os.path.join(OUT, 'rig_report.json'), 'w'), indent=1)
print('MARTA_RIG_OK', report, flush=True)
