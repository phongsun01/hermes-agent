# Profiles: Chạy nhiều Agent Hermes độc lập

Chạy nhiều agent Hermes độc lập trên cùng một máy — mỗi agent có cấu hình, API key, bộ nhớ (memory), phiên làm việc (session), kỹ năng (skill) và trạng thái gateway riêng biệt.

---

## Profile là gì?
Một **Profile** thực chất là một thư mục gốc (`HERMES_HOME`) riêng biệt của Hermes. Mỗi profile sẽ có một thư mục riêng chứa các tệp tin cấu hình và dữ liệu bao gồm: `config.yaml`, `.env`, `SOUL.md`, các quan sát/kỷ niệm (memories), phiên làm việc (sessions), kỹ năng (skills), tác vụ lập lịch (cron jobs), và cơ sở dữ liệu trạng thái (state database). 

Profiles giúp bạn chạy các agent riêng biệt cho các mục đích khác nhau — ví dụ như trợ lý lập trình, chatbot cá nhân, hoặc agent nghiên cứu — mà không làm xáo trộn dữ liệu của nhau.

Khi bạn tạo một profile, nó sẽ tự động trở thành một lệnh alias riêng trên hệ thống. Ví dụ: khi tạo profile tên là `coder`, bạn có thể trực tiếp chạy các lệnh như `coder chat`, `coder setup`, `coder gateway start`, v.v.

---

## Bắt đầu nhanh

```bash
hermes profile create coder       # Tạo profile mới và thiết lập lệnh alias "coder"
coder setup                       # Cấu hình API key và lựa chọn mô hình (model)
coder chat                        # Bắt đầu trò chuyện với agent coder
```

Chỉ đơn giản như vậy. Giờ đây `coder` đã hoạt động độc lập với cấu hình, bộ nhớ và trạng thái riêng.

---

## Tạo profile

> [!TIP]
> **Cách thiết lập nhanh nhất:** Chạy lệnh `hermes setup --portal` bên trong profile mới để đồng bộ cấu hình mô hình (models) và công cụ (tools) cùng lúc thông qua [Nous Portal](/docs/integrations/nous-portal).

### 1. Profile trống (Blank profile)
```bash
hermes profile create mybot
```
Lệnh này tạo một profile hoàn toàn mới cùng các kỹ năng mặc định đi kèm. Bạn chỉ cần chạy `mybot setup` để điền API key, chọn model và các token cho gateway.

Nếu bạn muốn sử dụng profile này làm agent thực thi công việc cho bảng Kanban (hoặc muốn điều phối viên Kanban tự động phân bổ tác vụ phù hợp), hãy thêm mô tả vai trò bằng tham số `--description` khi tạo:
```bash
hermes profile create researcher --description "Đọc mã nguồn và tài liệu bên ngoài, viết báo cáo phân tích."
```
Bạn cũng có thể cập nhật hoặc tự động tạo phần mô tả này sau bằng lệnh `hermes profile describe`.

### 2. Chỉ nhân bản cấu hình (`--clone`)
```bash
hermes profile create work --clone
```
Lệnh này sao chép các tệp cấu hình `config.yaml`, `.env`, `SOUL.md` và các kỹ năng (skills) từ profile hiện tại sang profile mới. Cả hai sẽ dùng chung API key, mô hình và khả năng tương tự, nhưng có lịch sử chat (sessions) và bộ nhớ (memory) hoàn toàn mới. Bạn có thể sửa tệp `~/.hermes/profiles/work/.env` để đổi API key khác, hoặc sửa `SOUL.md` của profile này để đổi tính cách của agent.

### 3. Nhân bản toàn bộ (`--clone-all`)
```bash
hermes profile create backup --clone-all
```
Sao chép **tất cả mọi thứ** — bao gồm cấu hình, API key, tính cách (SOUL), bộ nhớ, kỹ năng, các tác vụ cron, và các plugin. Đây là một bản sao hoạt động đầy đủ. 
*Lưu ý: Lịch sử từng phiên làm việc (session history, `state.db`), thư mục `backups/`, `state-snapshots/` và `checkpoints/` sẽ không được sao chép vì chúng thuộc về lịch sử chạy của profile nguồn và dung lượng có thể lên đến hàng chục GB.* Để sao lưu đầy đủ cả lịch sử, hãy dùng lệnh `hermes profile export` hoặc `hermes backup`.

### 4. Nhân bản từ một profile cụ thể
```bash
hermes profile create work --clone-from coder
```
Tham số `--clone-from <source>` chỉ định trực tiếp profile nguồn để nhân bản cấu hình/skills/SOUL. Bạn có thể kết hợp với `--clone-all` để sao chép toàn bộ dữ liệu của profile đó:
```bash
hermes profile create work-backup --clone-from coder --clone-all
```

> [!NOTE]
> **Bộ nhớ Honcho & Profiles:** Khi kích hoạt Honcho, thao tác clone sẽ tự động tạo một thực thể AI peer chuyên biệt cho profile mới trong khi vẫn chia sẻ chung không gian làm việc của người dùng. Mỗi profile sẽ xây dựng hệ thống quan sát và định danh riêng của nó.

---

## Sử dụng profile

### Command aliases (Alias lệnh)
Mỗi profile sau khi tạo sẽ tự động có một lệnh alias tương ứng nằm tại thư mục `~/.local/bin/<tên_profile>`:
```bash
coder chat                    # Chat với agent coder
coder setup                   # Cấu hình các cài đặt cho coder
coder gateway start           # Khởi chạy gateway của coder
coder doctor                  # Kiểm tra sức khỏe hệ thống của coder
coder skills list             # Liệt kê các kỹ năng của coder
coder config set model.default anthropic/claude-sonnet-4
```
Lệnh alias này hỗ trợ tất cả các lệnh con của `hermes` — thực chất nó sẽ chạy `hermes -p <tên_profile>` dưới nền.

### Sử dụng flag `-p` hoặc `--profile`
Bạn có thể chỉ định rõ profile khi chạy bất kỳ lệnh `hermes` nào:
```bash
hermes -p coder chat
hermes --profile=coder doctor
hermes chat -p coder -q "xin chào"    # Hoạt động ở bất kỳ vị trí nào trong câu lệnh
```

### Đặt làm profile mặc định (`hermes profile use`)
```bash
hermes profile use coder
hermes chat                   # Lệnh này bây giờ sẽ chat với profile coder
hermes tools                  # Cấu hình công cụ cho coder
hermes profile use default    # Chuyển về lại profile mặc định ban đầu
```
Lệnh này hoạt động tương tự như lệnh chuyển ngữ cảnh `kubectl config use-context` trong Kubernetes.

### Xác định profile đang hoạt động
Giao diện CLI luôn hiển thị rõ profile nào đang được chọn:
* **Con trỏ lệnh (Prompt)**: Hiển thị `coder ❯` thay vì chỉ có `❯`.
* **Banner**: Hiển thị `Profile: coder` khi khởi động.
* **Lệnh `hermes profile`**: Hiển thị chi tiết tên profile hiện tại, đường dẫn thư mục, mô hình mặc định đang dùng và trạng thái của gateway.

---

## Profiles vs Workspaces vs Sandboxing

Profiles thường bị nhầm lẫn với Workspace (không gian làm việc) hoặc Sandbox (môi trường cô lập), nhưng chúng có vai trò hoàn toàn khác nhau:
* **Profile**: Cung cấp thư mục lưu trữ trạng thái riêng cho Hermes (bao gồm `config.yaml`, `.env`, `SOUL.md`, sessions, memory, logs, cron jobs và trạng thái gateway).
* **Workspace / Working Directory**: Là thư mục hiện hành nơi các lệnh terminal bắt đầu chạy. Giá trị này được kiểm soát bởi cấu hình `terminal.cwd`.
* **Sandbox**: Là cơ chế giới hạn quyền truy cập hệ thống tệp tin. **Profiles không tự động tạo sandbox cho agent.**

Ở terminal backend mặc định (`local`), agent vẫn có quyền truy cập hệ thống tệp tin giống hệt như tài khoản người dùng hệ điều hành của bạn. Một profile không thể ngăn cản agent truy cập các thư mục nằm ngoài thư mục profile của nó.

Nếu bạn muốn một profile luôn bắt đầu chạy tại một thư mục dự án cụ thể, hãy cấu hình đường dẫn tuyệt đối cho `terminal.cwd` trong tệp `config.yaml` của profile đó:
```yaml
terminal:
  backend: local
  cwd: /duong-dan/tuyet-doi/toi/du-an
```
*Lưu ý: Đặt cấu hình `cwd: "."` ở backend `local` nghĩa là "thư mục mà lệnh Hermes được gọi", chứ không phải là "thư mục chứa dữ liệu profile".*

---

## Chạy các Gateway

Mỗi profile có thể khởi chạy một gateway độc lập dưới dạng một tiến trình riêng biệt với token bot riêng:
```bash
coder gateway start           # Chạy gateway cho coder
assistant gateway start       # Chạy gateway cho assistant (tiến trình riêng biệt)
```

### Cấu hình Bot Token riêng biệt
Vì mỗi profile có tệp `.env` riêng, bạn có thể chỉnh sửa để đặt các token bot Telegram/Discord/Slack riêng cho từng profile:
```bash
# Chỉnh sửa token của profile coder
nano ~/.hermes/profiles/coder/.env

# Chỉnh sửa token của profile assistant
nano ~/.hermes/profiles/assistant/.env
```

### Cơ chế khóa Token an toàn (Safety: token locks)
Nếu hai profile vô tình dùng chung một bot token, gateway khởi chạy sau sẽ bị chặn lại kèm theo thông báo lỗi ghi rõ tên profile đang xảy ra xung đột. Tính năng này được hỗ trợ trên các nền tảng Telegram, Discord, Slack, WhatsApp và Signal.

### Khởi tạo dịch vụ chạy cùng hệ thống (Persistent services)
```bash
coder gateway install         # Tạo service dạng systemd/launchd tên là hermes-gateway-coder
assistant gateway install     # Tạo service tên là hermes-gateway-assistant
```
Mỗi profile sẽ được đăng ký thành một dịch vụ riêng biệt và chạy độc lập.

> [!NOTE]
> **Đối với môi trường Docker:** Các gateway của từng profile được giám sát trực tiếp bởi `s6-overlay` (PID 1 trong container). Do đó, khi bạn chạy `hermes profile create <name>`, hệ thống sẽ tự động đăng ký một slot dịch vụ s6 tại `/run/service/gateway-<name>/`. Các lệnh bật/tắt/khởi động lại gateway của profile sẽ tương tác với `s6-svc` thay vì tạo tiến trình trực tiếp, đảm bảo gateway tự động khởi động lại khi gặp sự cố hoặc duy trì đúng trạng thái sau khi container restart.

---

## Cấu hình Profiles

Mỗi profile sở hữu các tệp tin cấu hình độc lập bao gồm:
* **`config.yaml`** — Định nghĩa mô hình, nhà cung cấp (provider), các bộ công cụ (toolsets) và mọi thiết lập vận hành.
* **`.env`** — Lưu trữ các khóa API (API keys) và bot tokens bảo mật.
* **`SOUL.md`** — Định hình tính cách, phong cách và chỉ dẫn nghiệp vụ cho agent.

```bash
coder config set model.default anthropic/claude-sonnet-4
echo "Bạn là một trợ lý tập trung chuyên biệt vào việc lập trình viết mã nguồn." > ~/.hermes/profiles/coder/SOUL.md
```

### Quản lý từ Web Dashboard
[Web Dashboard](/docs/user-guide/features/web-dashboard) là giao diện quản lý cấp máy chủ, cho phép bạn quản lý cấu hình, API keys, kỹ năng, MCPs và mô hình của **bất kỳ** profile nào thông qua bộ chuyển đổi profile (profile switcher) ở thanh bên (sidebar) — bạn không cần phải mở riêng dashboard cho từng profile. 

Lệnh `coder dashboard` sẽ mở Web Dashboard và tự động chọn sẵn profile `coder`. Tab Chat của dashboard cũng sẽ tuân theo cấu hình profile đang được chọn để tạo các phiên hội thoại tương ứng.

*Lưu ý: Tùy chọn "Set as active" trên trang Profiles của dashboard sẽ lưu lại cài đặt mặc định cho các phiên chạy CLI/gateway trong tương lai (tương đương với lệnh `hermes profile use`).*

---

## Cập nhật Profiles
Lệnh `hermes update` chỉ tải mã nguồn mới về một lần duy nhất (dùng chung cho toàn hệ thống) nhưng sẽ tự động đồng bộ hóa các kỹ năng mặc định (bundled skills) mới đến **tất cả** các profile:
```bash
hermes update
# → Mã nguồn đã được cập nhật
# → Đồng bộ kỹ năng: default (đã mới nhất), coder (+2 mới), assistant (+2 mới)
```
Các kỹ năng do người dùng tự chỉnh sửa sẽ không bao giờ bị ghi đè.

---

## Quản lý Profiles

```bash
hermes profile list           # Hiển thị danh sách tất cả profiles kèm trạng thái hoạt động
hermes profile show coder     # Xem thông tin chi tiết của một profile
hermes profile rename coder dev-bot   # Đổi tên profile (sẽ tự động cập nhật alias và service)
hermes profile export coder   # Xuất toàn bộ dữ liệu profile ra tệp nén coder.tar.gz
hermes profile import coder.tar.gz   # Nhập profile từ tệp nén sao lưu
```

---

## Xóa Profile
```bash
hermes profile delete coder
```
Lệnh này sẽ dừng gateway đang chạy, xóa dịch vụ systemd/launchd tương ứng, xóa lệnh alias và xóa toàn bộ dữ liệu của profile đó. Hệ thống sẽ yêu cầu bạn nhập lại tên profile để xác nhận trước khi thực hiện.

Để bỏ qua bước xác nhận, bạn có thể thêm flag `--yes`:
```bash
hermes profile delete coder --yes
```

> [!WARNING]
> Bạn không thể xóa profile mặc định của hệ thống (`~/.hermes`). Nếu bạn muốn gỡ bỏ hoàn toàn mọi dữ liệu và cấu hình của Hermes, hãy sử dụng lệnh `hermes uninstall`.

---

## Tự động hoàn thành lệnh (Tab completion)

```bash
# Đối với Bash
eval "$(hermes completion bash)"

# Đối với Zsh
eval "$(hermes completion zsh)"
```
Bạn hãy thêm dòng lệnh tương ứng vào tệp `~/.bashrc` hoặc `~/.zshrc` để duy trì tính năng này mỗi khi mở terminal mới. Giao diện dòng lệnh sẽ tự động gợi ý tên profile sau flag `-p`, các lệnh con của profile và các lệnh hệ thống.

---

## Cơ chế hoạt động

Hệ thống Profile hoạt động dựa trên biến môi trường `HERMES_HOME`. 

Khi bạn chạy lệnh `coder chat`, tệp kịch bản wrapper (trình bao) sẽ gán biến `HERMES_HOME=~/.hermes/profiles/coder` trước khi gọi chương trình `hermes`. Vì tất cả các tệp mã nguồn trong hệ thống Hermes đều phân giải đường dẫn thông qua hàm `get_hermes_home()`, toàn bộ dữ liệu trạng thái của Hermes — từ cấu hình, phiên làm việc, bộ nhớ, kỹ năng, nhật ký hoạt động (logs), tác vụ cron đến gateway — sẽ tự động được giới hạn trong thư mục của profile đó.

Điều này hoàn toàn độc lập với thư mục làm việc của terminal (`terminal.cwd`). 

### Quyền truy cập thư mục người dùng (`HOME`)
Theo mặc định trên hệ thống cài đặt trực tiếp (host installs), các tiến trình con thực thi công cụ của agent vẫn sẽ giữ nguyên biến môi trường `HOME` gốc của hệ điều hành. Điều này giúp các công cụ dòng lệnh hiện có của bạn (như `git`, `ssh`, `gh`, `az`, `npm`, Claude Code, Codex) tìm thấy và sử dụng chung các thông tin xác thực hiện tại mà không cần thiết lập lại.

* **`HERMES_HOME`**: Là ranh giới của profile. Nó kiểm soát cấu hình Hermes, tệp `.env`, bộ nhớ, phiên chat, kỹ năng, tác vụ cron, gateway, v.v.
* **`HOME`**: Là thư mục người dùng của hệ điều hành. Hermes giữ nguyên giá trị này để các công cụ dòng lệnh ngoài Hermes chạy mượt mà mà không bị mất quyền xác thực.

Nếu bạn cần cách ly hoàn toàn danh tính dòng lệnh cho từng profile, hãy thiết lập tùy chọn `terminal.home_mode: profile` trong tệp `config.yaml` của profile đó. Khi bật chế độ này:
1. Hermes sẽ chạy các tiến trình công cụ con với biến môi trường `HOME={HERMES_HOME}/home`.
2. Bạn sẽ cần phải thiết lập hoặc tạo liên kết (symlink) các tệp xác thực như thư mục `~/.ssh`, `~/.gitconfig`, cấu hình `gh`, cloud CLI auth, npm state... ngay bên trong thư mục con `home/` của profile đó.

Hermes đồng thời truyền biến `HERMES_REAL_HOME` vào các tiến trình con để các đoạn mã kịch bản vẫn có thể tìm lại được thư mục người dùng thật của hệ điều hành khi cần thiết.

---

## Chia sẻ profile dưới dạng bản phân phối (Profile Distributions)

Một profile bạn đã cấu hình tối ưu trên máy của mình có thể được đóng gói thành một **kho lưu trữ git (git repository)** để cài đặt nhanh chóng chỉ với một câu lệnh trên các máy tính khác — cho dù đó là máy trạm mới của bạn, máy của đồng nghiệp hay của cộng đồng người dùng. 

Bản phân phối chia sẻ này sẽ bao gồm: Tính cách (SOUL), cấu hình, các kỹ năng (skills), tác vụ cron và các kết nối MCP. Các thông tin xác thực (credentials), bộ nhớ (memories) và lịch sử chat (sessions) vẫn được giữ riêng tư theo từng máy.

```bash
# Cài đặt nguyên một agent từ một kho lưu trữ git
hermes profile install github.com/username/research-bot --alias

# Cập nhật phiên bản mới từ tác giả sau này (vẫn giữ lại bộ nhớ và tệp .env cá nhân của bạn)
hermes profile update research-bot
```

Để biết thêm chi tiết về cách đóng gói, phát hành, cơ chế cập nhật và chính sách bảo mật, hãy tham khảo tài liệu hướng dẫn **[Profile Distributions: Chia sẻ Agent hoàn chỉnh](file:///d:/Antigravity/Hermes/docs/profile-distributions-guide.md)**.
