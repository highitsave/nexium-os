# Supplied Mac icon pack hook — pending files

The intended source is Avery's supplied Mac icon pack, replacing the earlier
iOS 4 note. Only IMG-0874.jpeg, a preview/reference sheet, has been supplied.
It is not integrated, sliced or redrawn. No bespoke icons are generated.
Actual individual pack files and their usage rights remain needed.

Put the actual pack as a freedesktop theme in `branding/icons/supplied/`, with
`index.theme`, scalable/ or resolution directories (e.g. 48x48/apps/), and
Inherits=Adwaita. Or adapt mapping.json to map each provisional dock identity
to an existing icon name in that supplied theme. Do not stretch artwork.
The install hook copies that theme into /usr/share/icons/NexiumSupplied and
selects NexiumSupplied only when index.theme and valid mapped icons exist.
Otherwise Adwaita remains selected. Missing requested icons must fall back
to standard named icons, never generated substitute artwork. Re-run the
workflow after files arrive; review the dock arrangement with Avery then.
The current layout is a provisional implementation of the requested ten
entries, not a finalized supplied-icon design.
