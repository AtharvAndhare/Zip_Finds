
/* eslint-disable react/no-unknown-property */
import React, { useRef, useEffect, forwardRef, Suspense } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { EffectComposer, wrapEffect } from '@react-three/postprocessing';
import { Effect } from 'postprocessing';
import * as THREE from 'three';

import './Dither.css';

const waveVertexShader = `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

const waveFragmentShader = `
precision highp float;
uniform vec2 resolution;
uniform float time;
uniform float waveSpeed;
uniform float waveFrequency;
uniform float waveAmplitude;
uniform vec3 waveColor;

// Simplex 2D noise
vec3 permute(vec3 x) { return mod(((x*34.0)+1.0)*x, 289.0); }
float snoise(vec2 v){
  const vec4 C = vec4(0.211324865405187, 0.366025403784439,
           -0.577350269189626, 0.024390243902439);
  vec2 i  = floor(v + dot(v, C.yy) );
  vec2 x0 = v -   i + dot(i, C.xx);
  vec2 i1;
  i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
  vec4 x12 = x0.xyxy + C.xxzz;
  x12.xy -= i1;
  i = mod(i, 289.0);
  vec3 p = permute( permute( i.y + vec3(0.0, i1.y, 1.0 ))
  + i.x + vec3(0.0, i1.x, 1.0 ));
  vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy),
    dot(x12.zw,x12.zw)), 0.0);
  m = m*m ;
  m = m*m ;
  vec3 x = 2.0 * fract(p * C.www) - 1.0;
  vec3 h = abs(x) - 0.5;
  vec3 a0 = x - floor(x + 0.5);
  vec3 g = a0 * vec3(x0.x,x12.xz) + h * vec3(x0.y,x12.yw);
  vec3 ox = floor(a0 + 0.5);
  vec3 zh = 1.0 - 0.85 * ( ox*ox + h*h );
  vec3 ln = zh * ( zh * zh * ( 3.0 - 2.0 * zh ) );
  return 130.0 * dot(m, g);
}

void main() {
  vec2 uv = gl_FragCoord.xy / resolution.xy;
  float n = snoise(uv * waveFrequency + time * waveSpeed);
  float pattern = smoothstep(0.4, 0.6, n * waveAmplitude + 0.5);
  vec3 col = mix(vec3(0.05), waveColor, pattern);
  gl_FragColor = vec4(col, 1.0);
}
`;

const ditherFragmentShader = `
uniform float colorNum;
uniform float pixelSize;
const float bayerMatrix8x8[64] = float[64](
  0.0, 48.0, 12.0, 60.0, 3.0, 51.0, 15.0, 63.0,
  32.0, 16.0, 44.0, 28.0, 35.0, 19.0, 47.0, 31.0,
  8.0, 56.0, 4.0, 52.0, 11.0, 59.0, 7.0, 55.0,
  40.0, 24.0, 36.0, 20.0, 43.0, 27.0, 39.0, 23.0,
  2.0, 50.0, 14.0, 62.0, 1.0, 49.0, 13.0, 61.0,
  34.0, 18.0, 46.0, 30.0, 33.0, 17.0, 45.0, 29.0,
  10.0, 58.0, 6.0, 54.0, 9.0, 57.0, 5.0, 53.0,
  42.0, 26.0, 38.0, 22.0, 41.0, 25.0, 37.0, 21.0
);

void mainImage(in vec4 inputColor, in vec2 uv, out vec4 outputColor) {
  vec2 scaledCoord = floor(uv * resolution / pixelSize);
  int x = int(mod(scaledCoord.x, 8.0));
  int y = int(mod(scaledCoord.y, 8.0));
  float threshold = (bayerMatrix8x8[y * 8 + x] / 64.0) - 0.5;
  vec3 color = inputColor.rgb;
  color += threshold * (1.0 / colorNum);
  color = floor(color * colorNum + 0.5) / colorNum;
  outputColor = vec4(color, 1.0);
}
`;

class RetroEffectImpl extends Effect {
  constructor() {
    super('RetroEffect', ditherFragmentShader, {
      uniforms: new Map([
        ['colorNum', new THREE.Uniform(4.0)],
        ['pixelSize', new THREE.Uniform(2.0)]
      ])
    });
  }

  update(_renderer: any, _inputBuffer: any, _deltaTime: any) {
    // Basic update loop
  }
}

const WrappedRetro = wrapEffect(RetroEffectImpl);

const RetroEffect = forwardRef(({ colorNum = 4.0, pixelSize = 2.0 }: any, ref) => {
  return <WrappedRetro ref={ref} colorNum={colorNum} pixelSize={pixelSize} />;
});
RetroEffect.displayName = 'RetroEffect';

function DitheredWaves({ waveSpeed = 0.05, waveFrequency = 3, waveAmplitude = 0.3, waveColor = [0.33, 0.42, 0.18], colorNum = 4.0, pixelSize = 2.0 }: any) {
  const { viewport, size } = useThree();
  
  // Use a ref for uniforms to avoid recreating material every frame
  const uniforms = useRef({
    time: { value: 0 },
    resolution: { value: new THREE.Vector2(size.width, size.height) },
    waveSpeed: { value: waveSpeed },
    waveFrequency: { value: waveFrequency },
    waveAmplitude: { value: waveAmplitude },
    waveColor: { value: new THREE.Color(...waveColor) }
  });

  useEffect(() => {
    uniforms.current.resolution.value.set(size.width, size.height);
  }, [size]);

  useEffect(() => {
    uniforms.current.waveColor.value.set(...waveColor);
    uniforms.current.waveSpeed.value = waveSpeed;
    uniforms.current.waveFrequency.value = waveFrequency;
    uniforms.current.waveAmplitude.value = waveAmplitude;
  }, [waveColor, waveSpeed, waveFrequency, waveAmplitude]);

  useFrame((state) => {
    uniforms.current.time.value = state.clock.getElapsedTime();
  });

  // JSX intrinsic aliases to satisfy TS if needed
  const Mesh = 'mesh' as any;
  const PlaneGeometry = 'planeGeometry' as any;
  const ShaderMaterial = 'shaderMaterial' as any;

  return (
    <>
      <Mesh scale={[viewport.width, viewport.height, 1]}>
        <PlaneGeometry args={[1, 1]} />
        <ShaderMaterial
          vertexShader={waveVertexShader}
          fragmentShader={waveFragmentShader}
          uniforms={uniforms.current}
        />
      </Mesh>
      <EffectComposer disableNormalPass>
        <RetroEffect colorNum={colorNum} pixelSize={pixelSize} />
      </EffectComposer>
    </>
  );
}

export default function Dither(props: any) {
  return (
    <div className="dither-container">
      <Canvas camera={{ position: [0, 0, 1] }} dpr={1} gl={{ antialias: false, stencil: false, depth: false }}>
        <Suspense fallback={null}>
          <DitheredWaves {...props} />
        </Suspense>
      </Canvas>
    </div>
  );
}
