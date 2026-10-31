#!/usr/bin/env node
// Create synthetic 16:9 images for videos/_test so the pipeline can be checked
// without Flow. Red bars = the edges that 3:4 may crop. Green box = the 3:4
// safe zone. Yellow square = the subject, which must stay visible in every format.
//
//   node scripts/make-test-images.mjs
import { execFileSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { ROOT } from './lib.mjs';

const out = join(ROOT, 'videos/_test/assets/images');
mkdirSync(out, { recursive: true });
const colors = ['0x1d3557', '0x2a9d8f', '0x6a4c93', '0x8d5524'];
colors.forEach((c, i) => {
  const vf = [
    'drawgrid=w=160:h=160:t=1:c=white@0.2',
    'drawbox=x=0:y=0:w=300:h=1440:color=red@0.9:t=fill',
    'drawbox=x=2260:y=0:w=300:h=1440:color=red@0.9:t=fill',
    'drawbox=x=740:y=0:w=1080:h=1440:color=lime@0.9:t=8',
    'drawbox=x=1180:y=620:w=200:h=200:color=yellow@1:t=fill',
  ].join(',');
  const file = join(out, `s0${i + 1}.png`);
  execFileSync('ffmpeg', ['-y', '-v', 'error', '-f', 'lavfi', '-i', `color=c=${c}:s=2560x1440`, '-frames:v', '1', '-vf', vf, file]);
  console.log(file);
});
