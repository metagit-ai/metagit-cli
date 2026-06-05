## Guarded sync

- Default to **fetch** for repository refresh.
- Use **pull** or **clone** only with explicit operator approval.
- Run `metagit prompt workspace -k sync-safe --text-only -c {{ manifest_path }}` before mutation.
- Record sync outcomes in session notes via `metagit_session_update`.
