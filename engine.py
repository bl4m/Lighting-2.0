from ursina import *
from panda3d.core import Material as pdMaterial,Texture as pandaTexture,RenderState,DepthOffsetAttrib
from panda3d.core import GraphicsOutput,GraphicsPipe,FrameBufferProperties,WindowProperties,CullFaceAttrib

class Material(pdMaterial):
    def __init__(self,**kwargs):
        super().__init__()
        self.roughness:float
        self.metallic:float
        for key, value in kwargs.items():
            setattr(self,key,value)

    @property
    def color(self):
        return self.base_color
    @color.setter
    def color(self,color:Vec4):
        self.base_color = color


class ShadowCaster:
    def __init__(self,app:Ursina,light,render_color_map=False,show_frustum=False):

        self.window_properties = WindowProperties(size=(1024,1024))
        self.buffer_properties = FrameBufferProperties()
        self.buffer_properties.setRgbColor(1)
        self.buffer_properties.setAlphaBits(1)
        self.buffer_properties.setDepthBits(32)

        self.buffer = app.graphicsEngine.makeOutput(app.pipe, "offscreen buffer", -2,self.buffer_properties, self.window_properties,GraphicsPipe.BFRefuseWindow,
                                                app.win.getGsg(), app.win)

        self.depth_map = pandaTexture()
        if app.win.getGsg().getSupportsShadowFilter():
            self.depth_map.setMinfilter(pandaTexture.FTShadow)
            self.depth_map.setMagfilter(pandaTexture.FTShadow)

            self.depth_map.setWrapU(pandaTexture.WMBorderColor)
            self.depth_map.setWrapV(pandaTexture.WMBorderColor)
            self.depth_map.setBorderColor(Vec4(1, 1, 1, 1))
        
        self.buffer.addRenderTexture(self.depth_map, GraphicsOutput.RTMBindOrCopy,GraphicsOutput.RTPDepthStencil)

        if render_color_map:
            self.color_map = pandaTexture()
            self.buffer.addRenderTexture(self.color_map, GraphicsOutput.RTMBindOrCopy,GraphicsOutput.RTPColor)
        else:
            self.color_map = None
        
        self.camera = app.make_camera(self.buffer)

        if type(light) == DirectionalLight:
            lens = light._light.get_lens()
        else:
            lens = light.node().get_lens()
        lens.setNearFar(-50, 100)
        lens.setFilmSize((8, 8))
        self.camera.node().set_lens(lens)
        self.camera.reparent_to(light)

        state = RenderState.make(CullFaceAttrib.make(CullFaceAttrib.MCullCounterClockwise),DepthOffsetAttrib.make(-2))
        self.camera.node().setInitialState(state)
        print(self.camera.node().getInitialState())


        #debug
        if show_frustum:
            self.camera.node().show_frustum()
        app.render.set_shader_input("shadowMap",self.depth_map)
        
    
class LightingEngine(Entity):
    def __init__(self,app:Ursina,num_lights):
        super().__init__()
        self.app = app
        self.num_lights = num_lights
        self.sh = Shader(
    vertex="""
    #version 410

    uniform mat4 p3d_ModelViewProjectionMatrix;
    uniform mat4 p3d_ModelViewMatrix;
    uniform mat3 p3d_NormalMatrix;
    uniform mat4 p3d_ViewMatrix;
    
    uniform struct p3d_LightSourceParameters {
        vec4 color;
        vec4 position;
        mat4 shadowViewMatrix;
    } p3d_LightSource[<numLights>];

    in vec4 p3d_Vertex;
    in vec2 p3d_MultiTexCoord0;
    in vec3 p3d_Normal;
    in vec3 p3d_Tangent;

    out vec2 uv;
    out vec3 fragPos;
    out vec3 normal1;
    out mat3 TBN;
    out vec4 shadowPosition;
    
    
    void main(){
        gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
        uv = p3d_MultiTexCoord0;
        normal1 = p3d_NormalMatrix * p3d_Normal;
        fragPos = (p3d_ModelViewMatrix * p3d_Vertex).xyz;
        
        vec3 T = normalize(p3d_NormalMatrix * p3d_Tangent);
        vec3 N = normalize(p3d_NormalMatrix * p3d_Normal);
        //T = normalize(T - dot(T, N) * N); // Orthogonalize T to N
        vec3 B = cross(N, T); // Cross product to get B
        //vec3 B = normalize(p3d_Binormal);
        TBN = mat3(T, B, N);
        
        for (int i = 0; i < <numLights>;i++){
            if (p3d_LightSource[i].position.w != 1.0) {
                shadowPosition = p3d_LightSource[i].shadowViewMatrix * p3d_ModelViewMatrix * p3d_Vertex;
                }
            }
    }
    
    """.replace("<numLights>", str(num_lights)),
    fragment="""
    #version 410
    
    #define BIAS 0.01

    out vec4 FragColor;

    in vec2 uv;
    in vec3 fragPos;
    in vec3 normal1;
    in mat3 TBN;
    in vec4 shadowPosition;

    const float PI = 3.14159265359;

    uniform struct p3d_MaterialParameters {
        vec4 baseColor;
        float roughness;
        float metallic;
    } p3d_Material;
    
    //uniform sampler2D albedoMap;
    //uniform sampler2D normalMap;
    //uniform sampler2D metallicMap;
    //uniform sampler2D roughnessMap;
    uniform sampler2DShadow shadowMap;
    uniform sampler2D p3d_Texture0;
    uniform vec4 p3d_ColorScale;
    
    uniform mat3 p3d_NormalMatrix;
    
    uniform struct p3d_LightSourceParameters {
        vec4 color;
        vec4 position;
        mat4 shadowViewMatrix;
    } p3d_LightSource[<numLights>];
    
    uniform struct p3d_LightModelParameters {
    vec4 ambient;
} p3d_LightModel;

    float DistributionGGX(vec3 N, vec3 H, float roughness){
        float a = roughness * roughness;
        float a2 = a * a;
        float NdotH = max(dot(N, H),0.0);
        float NdotH2 = NdotH * NdotH;

        float denom = (NdotH2 * (a2 - 1.0) + 1.0);
        denom = PI * denom * denom;

        return a2/denom;
    }

    float GeometrySchlickGGX(float NdotV, float roughness){
        float r = roughness + 1.0;
        float k = (r * r) / 8.0;

        return NdotV / (NdotV * (1.0 - k) + k);
    }

    float GeometrySmith(vec3 N, vec3 V, vec3 L, float roughness){
        float NdotV = max(dot(N, V), 0.0);
        float NdotL = max(dot(N,L), 0.0);
        float ggx1 = GeometrySchlickGGX(NdotV, roughness);
        float ggx2 = GeometrySchlickGGX(NdotL, roughness);
        return ggx1 * ggx2;
    }
    
    float ShadowCalculation(vec4 fragPosLightSpace,vec3 normal,vec3 lightDir)
{
    vec3 projCoords = fragPosLightSpace.xyz / fragPosLightSpace.w;
    projCoords = projCoords * 0.5 + 0.5;

    if(projCoords.z > 1.0)
        return 0.0;

    // float closestDepth = textureProj(shadowMap,fragPosLightSpace);
    // float currentDepth = projCoords.z;
    // float bias = 0.0;  
    // float shadow = currentDepth - bias > closestDepth  ? 1.0 : 0.0;

    float shadow = 0.0;
    float totalSamples = 0.0;
    
    vec2 poissonDisk[7] = vec2[](
    vec2(-1, -1),
    vec2(-1, 0),
    vec2(0, -1),
    vec2(0, 0),
    vec2(0, 1),
    vec2(1, 0),
    vec2(1, 1)
);

  for (int i = 0; i < 7; ++i) {
      vec2 offset = poissonDisk[i] * 0.0006; // .001 is kernelSize (seperation)
      vec4 coord = fragPosLightSpace;
      coord.xy += offset;
      float closestDepth = textureProj(shadowMap, coord);
      shadow += projCoords.z - BIAS > closestDepth ? 1.0 : 0.0;
      totalSamples += 1;
  }
      shadow /= totalSamples;
      return shadow;
}

    vec3 fresnelSchlick(float cosTheta, vec3 F0){
        return F0 + (1.0 - F0) * pow(clamp(1.0 - cosTheta,0.0,1.0), 5.0);
    }
    
    void main(){
        
        vec3 albedo = pow(texture(p3d_Texture0,uv).rgb * p3d_Material.baseColor.rgb, vec3(2.2));
        //pow(texture(albedoMap,uv).rgb, vec3(2.2))
        
        float metallic = p3d_Material.metallic;
        float roughness = p3d_Material.roughness;
        //float metallic = texture(metallicMap, uv).r;
        //float roughness = texture(roughnessMap, uv).r;
        
        vec3 N = normalize(normal1);
        vec3 V = normalize(-fragPos);

        vec3 F0 = vec3(0.04);
        F0 = mix(F0, albedo, metallic);

        vec3 L0 = vec3(0.0);

        for (int i = 0; i < <numLights>;i++){
            vec3 L;
            float attenuation = 1.0;
            float shadow = 0.0;
            if (p3d_LightSource[i].position.w == 1.0) {
                // point light
                vec3 lightDir = p3d_LightSource[i].position.xyz - fragPos;
                float distance = length(lightDir);
                L = normalize(lightDir);
                attenuation = 1.0 / (distance * distance + 0.01);
            }
            else {
                // Directional light
                L = normalize(p3d_LightSource[i].position.xyz);
                shadow = ShadowCalculation(shadowPosition, N, L);
                
            }
            vec3 H = normalize(V + L);
            vec3 radiance = p3d_LightSource[i].color.rgb * 10.0;

            // cook torrence brdf
            float NDF = DistributionGGX(N,H, roughness);
            float G = GeometrySmith(N,V,L, roughness);
            vec3 F = fresnelSchlick(max(dot(H,V),0.0), F0);

            vec3 kS = F;
            vec3 kD = vec3(1.0) - kS;
            kD *= 1.0 - metallic;

            vec3 numerator = NDF * G * F;
            float denominator = 4.0 * max(dot(N,V),0.0) * max(dot(N,L),0.0) + 0.0001;
            vec3 specular = numerator / denominator;

            float NdotL = max(dot(N,L), 0.0);
            L0 += (1.0 - shadow) * ((kD * albedo / PI + specular) * radiance * NdotL);
        }

        vec3 ambient = p3d_LightModel.ambient.rgb * albedo;
        vec3 color = ambient + L0;

        color = color / (color + vec3(1.0));
        color = pow(color, vec3(1.0/2.2));

        FragColor = vec4(color,1.0);

    }
    
    """.replace("<numLights>", str(num_lights))
)
        self.sh.compile()
        self.app.render.setShader(self.sh._shader)

        self.default_material = Material(baseColor=Vec3(1,1,1), metalic=0, roughness=1)