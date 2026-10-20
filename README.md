# App Module Builder

Extensive app builder based on [j-hc](https://github.com/j-hc/revanced-magisk-module).

## Customization & Usage

 * Customize config.toml file to select apps and patches.
 * Run the build workflow in the Actions tab.
 * Grab your modules and APKs from the Releases section.

## Obtainium

Las publicaciones numéricas (`16`, `17`, etc.) son compilaciones conjuntas y
actualizaciones de módulos Magisk. **No son versiones de las aplicaciones.**
Una compilación puede incluir solo Twitter y no una actualización de Photos.

Los APK también se publican por aplicación con su versión en la etiqueta:
`googlephotos-devanced-v7.92.0.977185651`, por ejemplo. El workflow
**Publish existing APKs for Obtainium** recupera los últimos APK existentes de
las publicaciones numéricas sin recompilarlos ni cambiar sus firmas.
Las nuevas compilaciones mantienen estas publicaciones automáticamente.
Una recompilación de la misma versión conserva el APK publicado originalmente.

### Corregir una entrada existente

En Obtainium, abre la aplicación y edita sus opciones de origen usando la URL
`https://github.com/Jalec88/Morphe-apps` y estos ajustes:

| Ajuste | Valor |
| --- | --- |
| Filtro de títulos de publicaciones | Uno de los filtros de la tabla siguiente |
| Filtro de APK | Uno de los filtros de la tabla siguiente |
| Volver a publicaciones anteriores (fallback) | Activado |
| Usar título como versión | Desactivado |
| Recortar versión / expresión regular | `(?<=-v).+` |
| Grupo de coincidencia | `$0` |
| Detección/reconciliación de versión instalada | Activada |
| Usar código de versión como versión | Desactivado |
| Usar fecha de publicación como versión | Desactivado |
| Ordenar publicaciones | Fecha de publicación |

| Aplicación | Filtro de títulos | Filtro de APK |
| --- | --- | --- |
| Google Photos | `^googlephotos-devanced [0-9]` | `^googlephotos-devanced-v.*-all\.apk$` |
| YouTube | `^youtube-morphe [0-9]` | `^youtube-morphe-v.*-all\.apk$` |
| YouTube Music | `^music-morphe [0-9]` | `^music-morphe-v.*-(arm64-v8a\|arm-v7a)\.apk$` |
| Reddit | `^reddit-morphe [0-9]` | `^reddit-morphe-v.*-all\.apk$` |
| Twitter | `^twitter-piko [0-9]` | `^twitter-piko-v.*-all\.apk$` |

Para Music, conserva la selección automática de arquitectura. No selecciones
archivos `module.zip` como APK.

**“This app config may prevent updates”**: toca el aviso para ver su causa.
Si indica que varias publicaciones recientes fueron filtradas, es esperable
en este repositorio compartido: pueden corresponder a otras aplicaciones.
En las opciones de salud de actualizaciones de esa entrada puedes desactivar
solo la comprobación de **publicaciones filtradas**. Conserva las demás
comprobaciones; un error de red, descarga o instalación requiere revisar su
mensaje específico. Este ajuste no crea actualizaciones nuevas.

Guarda y vuelve a buscar actualizaciones. Photos debe mostrar la versión de
su APK (por ejemplo `7.92.0.977185651`), en lugar de `16`. Estos ajustes se
aplican en el teléfono: los cambios del repositorio no editan las entradas
ya guardadas en Obtainium. No hace falta desinstalar Google Photos.

## Building Locally

### On Termux
bash build-termux.sh

### On Linux
$ git clone <your-repo-url> --depth 1
$ cd <your-repo-folder>
$ ./build.sh
