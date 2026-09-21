/* A single georeferenced mask below the building layer, uploaded only on change. */
class GroundShadowLayer {
 constructor(canvas){this.id='live-shadows';this.type='custom';this.renderingMode='2d';this.canvas=canvas;this.dirty=true;this.bounds=null;}
 onAdd(map,gl){this.map=map;this.gl=gl;
  const shader=(type,source)=>{const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;};
  const vertex=shader(gl.VERTEX_SHADER,'#version 300 es\nin vec2 a_position;in vec2 a_uv;uniform mat4 u_matrix;out vec2 v_uv;void main(){gl_Position=u_matrix*vec4(a_position,0.0,1.0);v_uv=a_uv;}');
  const fragment=shader(gl.FRAGMENT_SHADER,'#version 300 es\nprecision highp float;uniform sampler2D u_mask;in vec2 v_uv;out vec4 fragColor;void main(){float a=texture(u_mask,v_uv).a*0.62;fragColor=vec4(vec3(27.0,29.0,34.0)/255.0*a,a);}');
  this.program=gl.createProgram();gl.attachShader(this.program,vertex);gl.attachShader(this.program,fragment);gl.linkProgram(this.program);gl.deleteShader(vertex);gl.deleteShader(fragment);if(!gl.getProgramParameter(this.program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(this.program));
  this.position=gl.getAttribLocation(this.program,'a_position');this.uv=gl.getAttribLocation(this.program,'a_uv');this.matrix=gl.getUniformLocation(this.program,'u_matrix');this.mask=gl.getUniformLocation(this.program,'u_mask');
  this.buffer=gl.createBuffer();this.texture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,this.texture);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
 }
 update(bounds){if(bounds)this.bounds=bounds;this.dirty=true;this.map?.triggerRepaint();}
 render(gl,args){if(!this.bounds)return;const b=this.bounds,nw=maplibregl.MercatorCoordinate.fromLngLat([b[0],b[3]]),se=maplibregl.MercatorCoordinate.fromLngLat([b[2],b[1]]);
  gl.useProgram(this.program);gl.bindBuffer(gl.ARRAY_BUFFER,this.buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([0,0,0,0,se.x-nw.x,0,1,0,0,se.y-nw.y,0,1,0,se.y-nw.y,0,1,se.x-nw.x,0,1,0,se.x-nw.x,se.y-nw.y,1,1]),gl.STREAM_DRAW);
  gl.enableVertexAttribArray(this.position);gl.vertexAttribPointer(this.position,2,gl.FLOAT,false,16,0);gl.enableVertexAttribArray(this.uv);gl.vertexAttribPointer(this.uv,2,gl.FLOAT,false,16,8);
  gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,this.texture);
  if(this.dirty){gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,false);gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,false);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,this.canvas);this.dirty=false;}
  // Translate the matrix in double precision; absolute Mercator float32 vertices lose metres.
  const m=Array.from(args.defaultProjectionData?.mainMatrix||args);for(let i=0;i<4;i++)m[12+i]+=m[i]*nw.x+m[4+i]*nw.y;
  gl.uniform1i(this.mask,0);gl.uniformMatrix4fv(this.matrix,false,m);gl.enable(gl.BLEND);gl.blendFunc(gl.ONE,gl.ONE_MINUS_SRC_ALPHA);gl.disable(gl.DEPTH_TEST);gl.drawArrays(gl.TRIANGLES,0,6);
 }
 onRemove(map,gl){gl.deleteTexture(this.texture);gl.deleteBuffer(this.buffer);gl.deleteProgram(this.program);}
}
