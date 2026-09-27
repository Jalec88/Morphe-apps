# App Module Builder

Extensive app builder based on j-hc.

<details><summary><big>Features</big></summary>
<ul>
 <li> Supports present and future app sources</li>
 <li> Receives in-app updates</li>
 <li> Can build modules and non-root APKs</li>
 <li> Optimizes APKs and modules for size</li>
 <li> Modules:
   <ul>
     <li> Recompile invalidated odex for faster usage</li>
     <li> Do not break safetynet or trigger root detections</li>
     <li> Handle installation of the correct version of the stock app</li>
     <li> Support Magisk and KernelSU</li>
   </ul>
 </li>
</ul>
</details>

## Customization & Usage

 * Customize config.toml file to select apps and patches.
 * Run the build workflow in the Actions tab.
 * Grab your modules and APKs from the Releases section.

## Building Locally

### On Termux
bash build-termux.sh

### On Linux
$ git clone <your-repo-url> --depth 1
$ cd <your-repo-folder>
$ ./build.sh
