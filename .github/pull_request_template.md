## 🏷️ Type

<!-- Chọn một. Tiêu đề PR theo Conventional Commits: feat(ordering): add COD checkout -->

- [ ] ✨ Feature
- [ ] 🐛 Bug
- [ ] ♻️ Refactor
- [ ] 🧹 Chore
- [ ] 📚 Docs

## 📌 Summary

**Làm gì:** <!-- Tóm tắt thay đổi trong 1–2 câu, theo hành vi mà người dùng hoặc hệ thống nhận thấy. Không liệt kê file (đã có ở Changes) -->

**Vì sao:** <!-- Vấn đề PR giải quyết: lỗi gì, thiếu gì, ticket yêu cầu gì, và hậu quả nếu không sửa. Người đọc không cần mở ticket vẫn hiểu -->

**Giải pháp:** <!-- Cách làm và lý do chọn cách đó thay vì phương án khác. Minh hoạ bằng pseudocode, call tree hoặc diff-sketch ngắn nhất đủ hiểu -->

**Kết quả:** <!-- Những gì đạt được sau PR so với trước, dạng Before → After: hành vi, số test, thời gian, lỗi. Bằng chứng ghi ở Cách kiểm; phần chưa đạt ghi ở Gap và lưu ý -->

**Module:** <!-- identity, catalog, inventory, promotions, payments, shipping, ordering, notifications, shared -->

**🔗 Closes:** `.scratch/<feature>/issues/NN-<slug>/` · **User story:** US-XXX · **Quy tắc:** BR-XXX

---

## 📋 Changes

<!-- Mỗi dòng: file hoặc nhóm file → thay đổi → lý do. Gom theo hành vi, không liệt kê từng file nhỏ -->

-
-
-

## 🔌 API / Migration / Cấu hình

<!-- Ghi "Không" cho mục không có -->

- **Endpoint:** <!-- thêm / đổi / bỏ, kèm method và path -->
- **Migration:** <!-- tên file, có đảo ngược được không -->
- **Biến môi trường, lệnh `make`:** <!-- tên mới, giá trị mặc định, đã thêm vào `.env.example` chưa -->

## 🧪 Cách kiểm

- **Tự động:** <!-- test chứng minh từng acceptance criterion: `file::test`; số test, coverage -->
- **Kiểm tay:** <!-- bước tái hiện và kết quả; "Không" nếu chỉ cần test tự động -->

---

## ⚠️ Gap và lưu ý

<!-- Bắt buộc. Mục nào không có thì ghi "Không", đừng xoá mục -->

- **Chưa làm:** <!-- phần của ticket còn thiếu, lý do; acceptance criterion chưa kiểm được -->
- **Gap / rủi ro:** <!-- chỗ tài liệu hoặc ticket sau phải xử lý, trường hợp biên chưa phủ, giới hạn đã biết -->
- **Quyết định tạm:** <!-- cách làm tạm thời, khi nào cần quay lại -->
- **Ticket mới:** <!-- việc ngoài phạm vi phát hiện được, đường dẫn ticket `needs-triage` -->
- **Reviewer cần chú ý:** <!-- đoạn code khó, chỗ lệch tài liệu có lý do, thay đổi trong `shared/` -->
- **Sau khi merge:** <!-- việc phải làm ở môi trường: chạy migrate, `make load-geo`, đặt biến môi trường; hoặc "Không" -->

---

## ✅ Checklist

- [ ] 🔨 Build pass: với thay đổi code đã chạy `make fmt`, `make lint` và test tương xứng; full `make test` trước merge/release
- [ ] 🧱 Ranh giới module: `lint-imports` xanh, chỉ gọi module khác qua `contracts.py`
- [ ] 🧪 Tested: có test cho service, handler hoặc API, kể cả trường hợp biên
- [ ] 🗄️ Migration: đã tạo nếu đổi model, tương thích ngược (hoặc N/A)
- [ ] 🌐 i18n: chuỗi hiển thị cho người dùng bọc `gettext` (hoặc N/A)
- [ ] 🔒 Security: không lộ secret, token, dữ liệu cá nhân thật trong code, log, test
- [ ] ⚡ Performance: không có N+1 query (`django-zeal` không báo)
- [ ] 📚 Docs: đã cập nhật GLOSSARY, business rules hoặc ADR nếu cần (hoặc N/A)
- [ ] 💥 Breaking change: ghi rõ trong *Gap và lưu ý* và thêm `!` vào tiêu đề PR (hoặc N/A)

---

## 💬 Notes

<!-- Thêm nếu có: kết luận review, bảng commit → task, link liên quan -->

---

📖 [Tài liệu dự án](../blob/main/README.md) · [Quy ước Git](../blob/main/docs/architecture/11-git-workflow.md)
