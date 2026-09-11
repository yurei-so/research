import json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector

args=sys.argv[sys.argv.index("--")+1:]
source,blend_path,image_path=map(Path,args)
data=json.loads(source.read_text())
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

def material(name,color):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    shader=m.node_tree.nodes.get('Principled BSDF'); shader.inputs['Base Color'].default_value=(*color,1)
    shader.inputs['Roughness'].default_value=.48
    return m
floor=material('floor',(0.025,0.035,0.055)); violet=material('agent paths',(0.48,0.22,1.0))
orange=material('resources',(0.95,0.48,0.08)); green=material('goal',(0.12,0.75,0.48)); wall=material('obstacles',(0.20,0.14,0.32))

bpy.ops.mesh.primitive_cube_add(location=(0,0,-.12),scale=(7,7,.1)); bpy.context.object.data.materials.append(floor)
for loc,scale in [((0,1.5,.5),(2,.25,.5)),((-2.7,-1,.5),(.25,1.5,.5))]:
    bpy.ops.mesh.primitive_cube_add(location=loc,scale=scale); bpy.context.object.data.materials.append(wall)
for loc in [(-4,4,.3),(4,-4,.3),(-4,-4,.3)]:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=.3,location=loc); bpy.context.object.data.materials.append(orange)
bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=1.1,depth=.03,location=(4,4,.02)); bpy.context.object.data.materials.append(green)

colors=[(0.62,0.28,1.0,1),(0.2,0.72,1.0,1),(1.0,0.35,0.55,1),(0.98,0.75,0.18,1)]
for index,replay in enumerate(data['replays']):
    segments=[]
    for row in replay['samples']:
        phase=row.get('phase',replay['policy'])
        if not segments or segments[-1][0] != phase: segments.append((phase,[]))
        segments[-1][1].append(row)
    for segment_index,(phase,rows) in enumerate(segments):
        samples=rows[::4]
        if len(samples) < 2: continue
        curve=bpy.data.curves.new(f'{replay["policy"]}-{phase}','CURVE'); curve.dimensions='3D'; curve.bevel_depth=.045
        spline=curve.splines.new('POLY'); spline.points.add(len(samples)-1)
        for point,row in zip(spline.points,samples): point.co=(row['x'],row['y'],.42+index*.04,1)
        obj=bpy.data.objects.new(f'{replay["policy"]}-{phase}',curve); bpy.context.collection.objects.link(obj)
        color_index=list(('explore','acquire','construct','recover')).index(phase) if phase in ('explore','acquire','construct','recover') else index
        mat=material(f'{replay["policy"]}-{phase}-{segment_index}',colors[color_index%len(colors)][:3]); obj.data.materials.append(mat)

bpy.ops.object.camera_add(location=(11,-13,13)); camera=bpy.context.object; bpy.context.scene.camera=camera
direction=Vector((0,0,0))-camera.location; camera.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
bpy.ops.object.light_add(type='AREA',location=(0,0,12)); bpy.context.object.data.energy=1800; bpy.context.object.data.shape='DISK'; bpy.context.object.data.size=8
scene=bpy.context.scene; scene.render.engine='BLENDER_EEVEE'; scene.render.resolution_x=1100; scene.render.resolution_y=800; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.filepath=str(image_path); scene.world.color=(0.008,0.012,0.022)
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path)); bpy.ops.render.render(write_still=True)
print('YUREI_BLENDER_EXPORT_OK',blend_path,image_path)
