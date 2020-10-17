# spotify-auto-playlists-from-library

Simple python script to generate Spotify playlists from your saved tracks. It will group them into playlists depending on the value of `group_tracks_by`. If the playlist already exists, the script will add any missing song. Tracks are added in from oldest to newest to the playlists.

The values of `group_tracks_by` can be:

- year (default): tracks will be grouped into playlists in basis to the add year. The format of the playlist name is `<year>`.
- month: tracks will be grouped into playlists in basis to the add year and month. The format of the playlist name is `<year> <month_num>`.
- quarter: tracks will be grouped into playlists in basis to the add year and quarter. The format of the playlist name is `<year> Q<quarter_num>`.

Note that you'll need to delete any playlist created manually.

## How to use

1. Get a Spotify token. Go to the [developer console](https://developer.spotify.com/console/get-several-albums/) and click on "Get Token". The required grants are `user-library-read` and `playlist-modify-public`.

2. Clone the repo

    ```bash
    git clone git@github.com:carpioldc/spotify-auto-playlists-from-library.git
    cd spotify-auto-playlists-from-library
    ```

3. Substitute the token on main.py
  
    ```bash
    sed -i "s/TOKEN_PLACEHOLDER/$put_your_token_here/g" main.py
    ```

4. Execute. You can do this setting the `dry_run = True` inside the script to see what will be done.

    ```bash
    ./main.py
    ```
