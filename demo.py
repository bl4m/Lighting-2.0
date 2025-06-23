from ursina import *
from engine import Material, LightingEngine, ShadowCaster

app = Ursina()

light = DirectionalLight(position=Vec3(1,2,3))
caster = ShadowCaster(app, light)
light.look_at(Vec3(0,0,0))

ambientLight = AmbientLight()
ambientLight.color = color.gray

PointLight(position=Vec3(1,0.5,0))



p = Entity(model='plane', scale=10)
m1 = Material(color=Vec4(0.08,0.2, 0.12,1.0),metallic=0.6, roughness=0.1)
p.setMaterial(m1)

q = Entity(model='cube',y=0.5)
m2 = Material(color=Vec4(1,0.1,0.2,1.0),metallic=0.1, roughness=0.4)
q.setMaterial(m2)

engine = LightingEngine(app, 2)
EditorCamera()

app.run()
